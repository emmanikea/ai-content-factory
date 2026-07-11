#!/usr/bin/env python3
"""
dual_server.py - serve the storefront pinned to ONE saved state (read-only), so two states can
run SIDE BY SIDE on two ports. The state-specific queue.json / approvals.json come from
_states/<state>/; all media (images, review frames + videos) is shared from this folder, so
nothing is duplicated.

Usage:
  python dual_server.py empty 8100     # the plain "before" store
  python dual_server.py done  8101     # the fully-populated "after" store (approved + videos)
"""
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).resolve().parent
STATE = sys.argv[1] if len(sys.argv) > 1 else "done"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8100
SDIR = SITE / "_states" / STATE


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SITE), **k)

    def _json_file(self, path: Path):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0].lstrip("/").rstrip("/")
        if p == "review/queue.json":
            return self._json_file(SDIR / "queue.json")
        if p == "approvals.json":
            return self._json_file(SDIR / "approvals.json")
        return super().do_GET()

    def do_POST(self):
        # read-only view: report the fixed approvals, never mutate
        try:
            data = json.loads((SDIR / "approvals.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {"approved": []}
        body = json.dumps({"ok": True, "approved": data.get("approved", [])}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not (SDIR / "queue.json").exists():
        sys.exit(f"state '{STATE}' not built. Run: python stage.py build")
    print(f"[{STATE}] serving on http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
