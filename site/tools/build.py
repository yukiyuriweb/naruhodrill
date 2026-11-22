# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""問題の検算・形式チェックと、公開用フォルダの作成。

    uv run site/tools/build.py          # チェックして site/data/index.json を作る（下書きも含む。開発用）
    uv run site/tools/build.py --dist   # さらに dist/ に公開する問題だけを書き出す

算数の問題は、問題文の条件だけから答えを総当たりで求め直し、
答えが 1 つに決まること・JSON の答えと一致することを確かめる。
"""

import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
DATA = SITE / "data"
DIST = SITE.parent / "dist"
SUBJECTS = ["math", "kokugo"]

# 小1〜3 で習う漢字。これ以外の漢字には、ふりがな {漢字|かんじ} を付ける
KANJI_G1_3 = set("".join(
    line.split()[1] for line in (Path(__file__).parent / "kanji_g1-3.txt").read_text(encoding="utf-8").splitlines()
    if line[:1].isdigit()
))
RUBY_RE = re.compile(r"\{[^|{}]+\|[^|{}]+\}")
KANJI_RE = re.compile(r"[\u4e00-\u9fff]")


# 漢字パズルで部品として見せるもの（読みは選択肢に「氵（さんずい）」のように書く）
COMPONENTS = set("氵亻扌")


def unruby_kanji(t: str) -> set[str]:
    """ふりがなの付いていない、小4以降の漢字"""
    return {k for k in KANJI_RE.findall(RUBY_RE.sub("", t)) if k not in KANJI_G1_3 | COMPONENTS}


def norm(t: str) -> str:
    """答えの比較と字数かぞえ用。ふりがなを外し、全角・半角をそろえ、空白を除く（common.js の normalize と同じ）"""
    t = re.sub(r"\{([^|{}]+)\|[^|{}]+\}", r"\1", t).replace("**", "")
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", t))

# 算数の指針 2.2・5.2 の禁止事項
MATH_BANNED = ["面積", "cm2", "cm²", "°", "周長", "線分", "代入", "方程式", "%", "％", "割合",
               "四捨五入", "概数", "通分", "約分", "速さ", "円周率", "3.14"]
MATH_BANNED_RE = [
    re.compile(r"(?<![A-Za-z])[a-fh-ln-su-zA-Z](?![A-Za-z])\s*[=＝]"),  # 文字式（x＝ など。単位 g・m・t は除く）
    re.compile(r"\d\s*[:：]\s*\d"),  # 比
    re.compile(r"\d\s*度"),  # 角度（「もう一度」は対象外）
]


# ---- 算数の検算（問題 ID ごと） ----

def math_001():
    # 円が たて2・よこ3 にぴったり。まわり 60cm。直径は 0.5cm 刻みで探す
    return [[d / 2, d / 4] for d in range(1, 400) if (3 * d / 2 + 2 * d / 2) * 2 == 60]


def math_002():
    # 7 でわると商 5、あまりあり
    ns = [n for n in range(1, 200) if n // 7 == 5 and n % 7 > 0]
    return [[min(ns), max(ns)]]


def math_003():
    # びん b + 水 w = 1200、b + w/2 = 750
    return [[w, b] for b in range(0, 1201) for w in range(0, 1201, 2) if b + w == 1200 and b + w // 2 == 750]


def perimeter(points):
    # 多角形の頂点（cm）を順にたどって、まわりの長さを出す
    return sum(abs(x2 - x1) + abs(y2 - y1) for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]))


def math_004():
    # たて6・よこ10 の長方形。ア：右上を たて2・よこ3 切り取る。イ：上の辺のまん中に はば2・ふかさ3 のみぞ
    a = perimeter([(0, 0), (10, 0), (10, 4), (7, 4), (7, 6), (0, 6)])
    b = perimeter([(0, 0), (10, 0), (10, 6), (6, 6), (6, 3), (4, 3), (4, 6), (0, 6)])
    return [[a, b]]


def math_005():
    # 十の位 a・一の位 b（1〜9）、ab + ba = 132。(1) a+b はどの解でも同じか (2) a-b=2 のときの ab
    pairs = [(a, b) for a in range(1, 10) for b in range(1, 10) if (10 * a + b) + (10 * b + a) == 132]
    sums = {a + b for a, b in pairs}
    nums = [10 * a + b for a, b in pairs if a - b == 2]
    return [[s, n] for s in sums for n in nums]


def math_006():
    # 30m に 5m おき。(1) かたがわ・両はしにも (2) 両がわ・両はしには うえない
    spots = list(range(0, 31, 5))
    return [[len(spots), (len(spots) - 2) * 2]]


def math_007():
    # バスは 7:10 から 15分おき。乗車 20分、学校まで 5分、8:30 までに着く。家からバスてい 8分
    buses = [7 * 60 + 10 + 15 * k for k in range(10)]
    ok = [b for b in buses if b + 20 + 5 <= 8 * 60 + 30]
    last = max(ok)
    leave = last - 8
    assert last // 60 == 7 and leave // 60 == 7  # 問題文が「7時何分」と聞いているため
    return [[last % 60, leave % 60]]


def math_008():
    # いちご 7目もり = 14人。みかん5・りんご4・ぶどう3
    bars = {"いちご": 7, "みかん": 5, "りんご": 4, "ぶどう": 3}
    unit = [u for u in range(1, 20) if bars["いちご"] * u == 14]
    return [[u, (bars["みかん"] - bars["ぶどう"]) * u, sum(bars.values()) * u] for u in unit]


def math_009():
    # 兄＋弟＝1000、兄＝弟＋200
    return [[y, a] for y in range(0, 1001) for a in range(0, 1001) if y + a == 1000 and a - y == 200]


def math_010():
    # 30円のあめ x こ、50円のガム y こ。x+y=8、30x+50y=300
    return [[y, x] for x in range(0, 9) for y in range(0, 9) if x + y == 8 and 30 * x + 50 * y == 300]


def math_011():
    # 公園を通る道 1400m、川ぞい 950m、家→公園 600m。(1) 公園→学校 (2) 行き公園・帰り川ぞい
    return [[x, 1400 + 950] for x in range(0, 1401) if 600 + x == 1400]


def math_012():
    # 30人が 4人がけの長いすに。(1) いる長いすの数 (2) さいごの長いすの人数
    n = min(k for k in range(1, 31) if 4 * k >= 30)
    return [[n, 30 - 4 * (n - 1)]]


def math_013():
    # ある数に 6 をたしたら 15。正しくは 6 をかける
    return [[n, n * 6] for n in range(0, 100) if n + 6 == 15]


def math_014():
    # 30cm のはり金で (1) 正三角形 (2) ちがう辺 8cm の二等辺三角形
    return [[e, s] for e in range(1, 31) for s in range(1, 31) if 3 * e == 30 and 2 * s + 8 == 30]


def math_015():
    # 0.1L を 1 として整数で。やかん 15、水とう 8 が 2つ
    left = 15 - 8
    return [[left / 10, (8 - left) / 10]]


def math_016():
    # 1辺 n こで正方形のまわりにならべる。実際に格子を数える
    def count(n):
        return sum(1 for i in range(n) for j in range(n) if i in (0, n - 1) or j in (0, n - 1))
    return [[count(5), count(10)]]


def math_017():
    # 3・0・7・1・5 で 5けた。(1) 最大 (2) 最小 (3) 50000 にいちばん近い
    from itertools import permutations
    ns = [int("".join(p)) for p in permutations("30715") if p[0] != "0"]
    best = min(abs(n - 50000) for n in ns)
    near = [n for n in ns if abs(n - 50000) == best]
    return [[max(ns), min(ns), x] for x in near]


def math_018():
    # ア6 × 7 ＝ イ2ウ
    return [[a, p] for a in range(1, 10) for p in [(10 * a + 6) * 7] if 100 <= p <= 999 and p // 10 % 10 == 2]


def math_019():
    # 8月1日が日曜日、31日まで。(3) は選択肢 ① 月 ② 火 ③ 水 ④ 木
    week = "日月火水木金土"
    sundays = [d for d in range(1, 32) if (d - 1) % 7 == 0]
    sep1 = week[31 % 7]
    return [[len(sundays), max(sundays), "月火水木".index(sep1) + 1]]


def math_020():
    # 32人。犬 12、ねこ 9、両方 4
    return [[d, n] for d in range(33) for c in range(33) for n in range(33)
            if d + 4 == 12 and c + 4 == 9 and d + c + 4 + n == 32]


SOLVERS = {f"math/{i:03d}": globals()[f"math_{i:03d}"] for i in range(1, 21)}


def texts(p, for_child=True):
    yield p["title"]
    yield from p["body"]
    for part in p["parts"]:
        yield part["prompt"]
        for c in part.get("choices", []):
            yield c["label"]
    yield from p["hints"]
    yield from p["explanation"]
    for m in p.get("mistakes", []):
        yield m["message"]
    if not for_child:
        yield from p.get("parent_note", [])


def check(path: Path, subject: str) -> list[str]:
    errs = []
    p = json.loads(path.read_text(encoding="utf-8"))
    need = ["id", "subject", "status", "title", "lv", "area", "hint_interval_min", "body", "parts",
            "hints", "mistakes", "explanation", "parent_note"]
    errs += [f"{k} がない" for k in need if k not in p]
    if errs:
        return errs
    if p["id"] != path.stem or p["subject"] != subject:
        errs.append("id・subject がファイルの場所と合っていない")
    if p["status"] not in ("draft", "published"):
        errs.append(f"status が不正: {p['status']}")
    if not (isinstance(p["hint_interval_min"], int) and 1 <= p["hint_interval_min"] <= 10):
        errs.append("hint_interval_min は 1〜10 の整数")
    if len(p["hints"]) != 3:
        errs.append(f"ヒントが 3 つでない: {len(p['hints'])}")
    if p.get("figure") and not (SITE / p["figure"]).exists():
        errs.append(f"図がない: {p['figure']}")

    for i, part in enumerate(p["parts"]):
        a = part.get("answer", {})
        if a.get("type") == "number":
            if not isinstance(a.get("value"), (int, float)):
                errs.append(f"{part['label']} の答えが数でない")
        elif a.get("type") == "choice":
            values = [c["value"] for c in part.get("choices", [])]
            if a.get("value") not in values or len(set(values)) != len(values):
                errs.append(f"{part['label']} の選択肢と答えが合わない")
        elif a.get("type") == "text":
            v = a.get("value")
            if not (isinstance(v, str) and norm(v)) or not all(isinstance(x, str) for x in a.get("accept", [])):
                errs.append(f"{part['label']} の答えが文字でない")
                continue
            # 字数指定：答えの字数と、問題文の「◯字」が合っているか（1字の狂いもないこと）
            if "chars" in a:
                if len(norm(v)) != a["chars"]:
                    errs.append(f"{part['label']} の字数が合わない: 「{norm(v)}」は {len(norm(v))} 字、chars は {a['chars']}")
                if f"{a['chars']}字" not in norm(part["prompt"]):
                    errs.append(f"{part['label']} の問題文に「{a['chars']}字」がない")
            # 書きぬき：本文にそのままあるか。答えに小4以降の漢字を入れない（採点がぶれるため）
            if a.get("from_body"):
                if norm(v) not in norm("".join(p["body"])):
                    errs.append(f"{part['label']} の答え「{norm(v)}」が本文にそのままない")
                if RUBY_RE.search(v) or unruby_kanji(v):
                    errs.append(f"{part['label']} の書きぬきの答えに、小4以降の漢字がある")
        else:
            errs.append(f"{part['label']} の答えの形が不明: {a.get('type')}")
    for m in p["mistakes"]:
        if not (0 <= m["part"] < len(p["parts"])):
            errs.append(f"mistakes の part が範囲外: {m}")
        elif str(m["value"]) == str(p["parts"][m["part"]]["answer"]["value"]):
            errs.append(f"mistakes に正解が入っている: {m}")

    # 子どもが読む文（親向けメモは除く）：ふりがなと、指針の禁止事項
    for t in texts(p):
        if (ks := unruby_kanji(t)):
            errs.append(f"ふりがなが要る漢字 {''.join(sorted(ks))}: {t}")
        if subject == "math":
            errs += [f"禁止語「{w}」: {t}" for w in MATH_BANNED if w in t]
            errs += [f"禁止パターン {r.pattern}: {t}" for r in MATH_BANNED_RE if r.search(t)]
    for t in texts(p, for_child=False):
        if t.count("{") != t.count("}") or t.count("**") % 2:
            errs.append(f"ふりがな・太字の記号が閉じていない: {t}")

    if subject == "math":
        solver = SOLVERS.get(f"math/{p['id']}")
        if solver is None:
            errs.append("検算の関数がない（SOLVERS に追加すること）")
        else:
            sols = solver()
            given = [part["answer"]["value"] for part in p["parts"]]
            if len(sols) != 1:
                errs.append(f"答えが 1 つに決まらない: {sols}")
            elif [float(x) for x in sols[0]] != [float(x) for x in given]:
                errs.append(f"答えが違う: 検算 {sols[0]} / JSON {given}")
    return errs


def main():
    index = {s: [] for s in SUBJECTS}
    bad = 0
    for subject in SUBJECTS:
        for path in sorted((DATA / subject).glob("[0-9][0-9][0-9].json")):
            errs = check(path, subject)
            print(f"{subject}/{path.name}: {'OK' if not errs else 'NG'}")
            for e in errs:
                print(f"  - {e}")
            bad += bool(errs)
            p = json.loads(path.read_text(encoding="utf-8"))
            index[subject].append({k: p.get(k) for k in ("id", "title", "lv", "area", "status")})
    (DATA / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if bad:
        sys.exit(1)

    if "--dist" in sys.argv:
        # 公開用：下書きの問題と開発用ファイルを除いて dist/ に書き出す
        if DIST.exists():
            shutil.rmtree(DIST)
        shutil.copytree(SITE, DIST, ignore=shutil.ignore_patterns("tools", "data", "review.html", "access.html", ".DS_Store"))
        published = {s: [x for x in index[s] if x["status"] == "published"] for s in SUBJECTS}
        for s in SUBJECTS:
            (DIST / "data" / s).mkdir(parents=True, exist_ok=True)
            for x in published[s]:
                shutil.copy(DATA / s / f"{x['id']}.json", DIST / "data" / s / f"{x['id']}.json")
        (DIST / "data" / "index.json").write_text(json.dumps(published, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"dist/ に書き出しました（公開: {sum(len(v) for v in published.values())} 問）")


if __name__ == "__main__":
    main()
