from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        text = body.decode("utf-8", errors="replace")
        print("\\n=== Incoming POST ===")
        print("Path:", self.path)
        try:
            obj = json.loads(text)
            print(json.dumps(obj, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(text)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8080
    print(f"Listening on http://{host}:{port}")
    HTTPServer((host, port), Handler).serve_forever()
