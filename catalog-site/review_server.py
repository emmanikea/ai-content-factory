#!/usr/bin/env python3
"""
review_server.py - serves the Camber storefront AND the human-in-the-loop approvals API.

Static files (index.html, images/, review/, *.json) + one endpoint:
  POST /api/approve   {"concept_id": "...", "approved": true|false}
      -> toggles the concept in approvals.json and returns the current approved list.

approvals.json is the gate the render workflow (content-factory-render) reads. Run:
  python review_server.py   # serves on http://127.0.0.1:8100
"""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).resolve().parent
APPROVALS = SITE / "approvals.json"
PORT = 8100


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SITE), **k)

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") != "/api/approve":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:  # noqa: BLE001
            return self._json(400, {"error": str(e)})
        data = {"approved": []}
        if APPROVALS.exists():
            try:
                data = json.loads(APPROVALS.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                data = {"approved": []}
        approved = set(data.get("approved", []))
        cid = body.get("concept_id")
        if not cid:
            return self._json(400, {"error": "concept_id required"})
        if body.get("approved"):
            approved.add(cid)
        else:
            approved.discard(cid)
        data["approved"] = sorted(approved)
        APPROVALS.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._json(200, {"ok": True, "approved": data["approved"]})

    def log_message(self, *a):  # quieter
        pass


if __name__ == "__main__":
    if not APPROVALS.exists():
        APPROVALS.write_text(json.dumps({"approved": []}, indent=2), encoding="utf-8")
    print(f"Review server on http://127.0.0.1:{PORT}  (approvals -> {APPROVALS.name})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
