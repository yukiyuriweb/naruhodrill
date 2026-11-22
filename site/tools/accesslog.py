# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""アクセスログの取得と集計（管理者の Mac でだけ使う）。

    uv run site/tools/accesslog.py fetch      # 今日の分を取得して logs/access/ にためる
    uv run site/tools/accesslog.py summary 7  # 直近 7 日の集計を JSON で出す

Xserver の API（xserver CLI）は「その日の」アクセスログしか返さないので、
日ごとに取得してためておく。何度取得しても同じ行は二重に保存しない。

保存先の logs/ は git にも公開用の dist/ にも入れない。
IP アドレスはそのまま保存せず、IP と User-Agent から作ったハッシュ（訪問者の目印）だけを残す。
"""

import hashlib
import json
import re
import secrets
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent.parent
LOGS = ROOT / "logs" / "access"
SALT = ROOT / "logs" / ".salt"
STATE = ROOT / "logs" / "last_fetch.json"

DOMAIN = "yukiyuriweb.com"  # ログはこのドメインのものに、サブドメインの分もまとめて入っている
HOST = "naruhodrill.yukiyuriweb.com"

PAGES = {"/": "トップ", "/index.html": "トップ", "/problem.html": "問題", "/dashboard.html": "がんばり",
         "/records.html": "きろく", "/about.html": "このサイトについて"}
BOT_RE = re.compile(r"bot|crawl|spider|slurp|facebookexternalhit|preview|curl|wget|python|go-http|headless|monitor|lighthouse", re.I)
LINE_RE = re.compile(
    r'^(?P<host>\S+) (?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<target>\S+)[^"]*" '
    r'(?P<status>\d{3}) (?P<size>\S+) "(?P<ref>[^"]*)" "(?P<ua>[^"]*)"')


def salt() -> str:
    if not SALT.exists():
        SALT.parent.mkdir(parents=True, exist_ok=True)
        SALT.write_text(secrets.token_hex(16))
    return SALT.read_text().strip()


def parse(line: str, s: str):
    m = LINE_RE.match(line)
    if not m or m["host"] != HOST:
        return None
    t = datetime.strptime(m["time"], "%d/%b/%Y:%H:%M:%S %z")
    return {
        "h": hashlib.sha256(line.encode()).hexdigest()[:20],  # 同じ行を二重に保存しないため
        "t": t.isoformat(),
        "vid": hashlib.sha256(f"{s}|{m['ip']}|{m['ua']}".encode()).hexdigest()[:16],
        "method": m["method"], "target": m["target"], "status": int(m["status"]),
        "ref": m["ref"], "ua": m["ua"],
    }


def fetch() -> dict:
    out = subprocess.run(
        ["xserver", "--format", "json", "server", "log", "access", "--domain", DOMAIN, "--keyword", HOST.split(".")[0],
         "--lines", "100000"],
        capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"xserver CLI が失敗しました: {out.stderr.strip()[:300]}")
    s = salt()
    rows = [r for r in (parse(l, s) for l in json.loads(out.stdout).get("log", "").splitlines()) if r]

    LOGS.mkdir(parents=True, exist_ok=True)
    added = 0
    for day in sorted({r["t"][:10] for r in rows}):
        path = LOGS / f"{day}.jsonl"
        have = {json.loads(l)["h"] for l in path.read_text().splitlines()} if path.exists() else set()
        new = [r for r in rows if r["t"][:10] == day and r["h"] not in have]
        with path.open("a", encoding="utf-8") as f:
            for r in new:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        added += len(new)
    state = {"fetchedAt": datetime.now().astimezone().isoformat(timespec="seconds"), "lines": len(rows), "added": added}
    STATE.write_text(json.dumps(state, ensure_ascii=False))
    return state


def device(ua: str) -> str:
    if "iPad" in ua:
        return "iPad"
    if "iPhone" in ua:
        return "iPhone"
    if "Android" in ua:
        return "Android"
    if "Macintosh" in ua:
        return "Mac（iPad のデスクトップ表示を含む）"
    if "Windows" in ua:
        return "Windows"
    if "CrOS" in ua:
        return "Chromebook"
    return "その他"


def summary(days: int) -> dict:
    today = date.today()
    keys = [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    daily = {k: {"pv": 0, "visitors": set(), "problems": 0} for k in keys}
    pages, problems, devices, refs, notfound = Counter(), Counter(), Counter(), Counter(), Counter()
    visitors_dev = {}
    bots = 0
    for k in keys:
        path = LOGS / f"{k}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            u = urlsplit(r["target"])
            if r["status"] == 404:
                notfound[u.path] += 1
            if r["method"] != "GET" or r["status"] not in (200, 304) or u.path not in PAGES:
                continue
            if BOT_RE.search(r["ua"]):
                bots += 1
                continue
            d = daily[k]
            d["pv"] += 1
            d["visitors"].add(r["vid"])
            pages[PAGES[u.path]] += 1
            visitors_dev[r["vid"]] = device(r["ua"])
            if u.path == "/problem.html":
                q = parse_qs(u.query)
                if q.get("s") and q.get("id"):
                    problems[f"{q['s'][0]}/{q['id'][0]}"] += 1
                    d["problems"] += 1
            ref = urlsplit(r["ref"]).hostname if r["ref"] not in ("", "-") else None
            if ref and ref != HOST:
                refs[ref] += 1
    devices.update(visitors_dev.values())
    all_visitors = set().union(*(d["visitors"] for d in daily.values()))
    stored = sorted(p.stem for p in LOGS.glob("*.jsonl")) if LOGS.exists() else []
    return {
        "days": days,
        "daily": [{"date": k, "pv": v["pv"], "visitors": len(v["visitors"]), "problems": v["problems"]} for k, v in daily.items()],
        "totals": {"pv": sum(v["pv"] for v in daily.values()), "visitors": len(all_visitors),
                   "problems": sum(v["problems"] for v in daily.values()), "bots": bots},
        "pages": pages.most_common(),
        "problems": problems.most_common(20),
        "devices": devices.most_common(),
        "referrers": refs.most_common(10),
        "notFound": notfound.most_common(10),
        "stored": {"from": stored[0] if stored else None, "to": stored[-1] if stored else None, "count": len(stored)},
        "lastFetch": json.loads(STATE.read_text()) if STATE.exists() else None,
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    if cmd == "fetch":
        print(json.dumps(fetch(), ensure_ascii=False))
    elif cmd == "summary":
        print(json.dumps(summary(int(sys.argv[2]) if len(sys.argv) > 2 else 7), ensure_ascii=False, indent=1))
    else:
        sys.exit(__doc__)
