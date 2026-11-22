# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""開発用のサーバー（自分の Mac でだけ使う）。

    uv run site/tools/serve.py          # http://localhost:8002/
    uv run site/tools/serve.py 8003     # ポートを変える

site/ をそのまま配信し、確認ページ（review.html）からの「公開・下書きの切り替え」を受けて、
問題の JSON の status と data/index.json を書き換える。外からはつながらないよう 127.0.0.1 で待ち受ける。
"""

import json
import re
import socket
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import accesslog

SITE = Path(__file__).resolve().parent.parent
DATA = SITE / "data"
SUBJECTS = ["math", "kokugo", "logic", "spatial"]
STATUSES = ["draft", "published"]
STATUS_RE = re.compile(r'^(\s*"status":\s*)"[a-z]+"', re.M)


def set_status(subject: str, pid: str, status: str):
    # JSON の書式を崩さないよう、status の行だけを書き換える
    path = DATA / subject / f"{pid}.json"
    text = path.read_text(encoding="utf-8")
    new, n = STATUS_RE.subn(rf'\1"{status}"', text, count=1)
    if n != 1:
        raise ValueError("status の行が見つからない")
    json.loads(new)  # 壊れていないか
    path.write_text(new, encoding="utf-8")

    # 目次（index.json）も合わせる。書式は build.py と同じ
    ipath = DATA / "index.json"
    index = json.loads(ipath.read_text(encoding="utf-8"))
    for x in index.get(subject, []):
        if x["id"] == pid:
            x["status"] = status
    ipath.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_json(self, obj, code=200):
        out = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        # アクセスログの集計（access.html から）。日数は 1〜90
        if self.path.startswith("/api/accesslog"):
            m = re.fullmatch(r"/api/accesslog\?days=(\d{1,2})", self.path)
            days = int(m.group(1)) if m else 7
            return self.send_json(accesslog.summary(min(max(days, 1), 90)))
        super().do_GET()

    def do_POST(self):
        # ほかのサイトから送らせないよう、同じ場所から来たものだけ受け付ける
        port = self.server.server_address[1]
        origin = self.headers.get("Origin")
        if origin not in (f"http://localhost:{port}", f"http://127.0.0.1:{port}"):
            return self.send_error(403)
        if self.path == "/api/accesslog/fetch":
            try:
                return self.send_json(accesslog.fetch())
            except Exception as e:  # CLI の失敗などは画面にそのまま出す
                return self.send_json({"error": str(e)}, 500)
        if self.path != "/api/status":
            return self.send_error(404)
        if self.headers.get("Content-Type") != "application/json":
            return self.send_error(415)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            subject, pid, status = body["subject"], body["id"], body["status"]
            if subject not in SUBJECTS or not re.fullmatch(r"\d{3}", pid) or status not in STATUSES:
                raise ValueError("値が不正")
            if not (DATA / subject / f"{pid}.json").exists():
                raise ValueError("問題がない")
            set_status(subject, pid, status)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            return self.send_error(400, "bad request")
        out = json.dumps({"ok": True, "status": status}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


class Server(ThreadingHTTPServer):
    request_queue_size = 64  # 問題をまとめて読みこむので、同時の接続を多めに受ける


class Server6(Server):
    address_family = socket.AF_INET6


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8002
    handler = partial(Handler, directory=str(SITE))
    # localhost は IPv6（::1）で来ることもあるので、両方で待ち受ける。どちらもこの Mac の中からだけ
    threading.Thread(target=Server6(("::1", port), handler).serve_forever, daemon=True).start()
    print(f"http://localhost:{port}/review.html （止めるときは Ctrl+C）")
    Server(("127.0.0.1", port), handler).serve_forever()


if __name__ == "__main__":
    main()
