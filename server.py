"""Local HTTP API for x-media-grabber (stdlib only).

Designed so a webpage can drive the tool:
  GET  /                        -> demo page (web/index.html)
  GET  /api/templates           -> allowed template variables + defaults
  POST /api/validate            -> {dir_template, file_template} -> {ok | error}
  POST /api/jobs                -> start job -> {id}
  GET  /api/jobs                -> [{id, status, done_users, total_users, ...}]
  GET  /api/jobs/<id>           -> full job incl. summary when finished

Progress is poll-based (GET /api/jobs/<id>) - simplest to merge into any page.
Run:  python grab.py serve --port 8765
"""

import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from x_media_grabber.jobs import run
from x_media_grabber.naming import DIR_VARS, FILE_VARS, validate_template
from x_media_grabber.sources import load_handles

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DEFAULT_OUT = str(ROOT / "downloads")

_jobs = {}
_seq = 0
_lock = threading.Lock()


def _new_id():
    global _seq
    with _lock:
        _seq += 1
        return f"job-{_seq}-{int(time.time())}"


class Handler(BaseHTTPRequestHandler):
    server_version = "XMediaGrabber/0.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path):
        target = (WEB_DIR / path.lstrip("/")).resolve()
        if WEB_DIR not in target.parents and target != WEB_DIR:
            return self._json({"error": "forbidden"}, 403)
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            return self._json({"error": "not found"}, 404)
        ctype = {".html": "text/html; charset=utf-8",
                 ".js": "application/javascript",
                 ".css": "text/css"}.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            return self._static("index.html")
        if parsed.path == "/api/templates":
            return self._json({"dir_vars": list(DIR_VARS), "file_vars": list(FILE_VARS),
                               "dir_default": "{handle}",
                               "file_default": "{handle}_{date}_{tweet_id}_{seq}.{ext}"})
        if parsed.path == "/api/jobs":
            with _lock:
                items = [{k: j[k] for k in ("id", "status", "done_users",
                                            "total_users", "current", "error",
                                            "created_at") if k in j}
                         for j in _jobs.values()]
            return self._json(items)
        if parsed.path.startswith("/api/jobs/"):
            jid = parsed.path.rsplit("/", 1)[-1]
            with _lock:
                job = _jobs.get(jid)
                snapshot = dict(job) if job else None
            if not snapshot:
                return self._json({"error": "job not found"}, 404)
            snapshot.pop("events", None)
            return self._json(snapshot)
        return self._static(parsed.path)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            return None

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        data = self._body()
        if data is None:
            return self._json({"error": "invalid JSON"}, 400)
        if parsed.path == "/api/validate":
            try:
                validate_template(data.get("dir_template", "{handle}"), "dir")
                validate_template(data.get("file_template", "{handle}_{date}_{tweet_id}_{seq}.{ext}"), "file")
            except ValueError as exc:
                return self._json({"ok": False, "error": str(exc)})
            return self._json({"ok": True})
        if parsed.path == "/api/jobs":
            try:
                validate_template(data.get("dir_template", "{handle}"), "dir")
                validate_template(data.get("file_template", "{handle}_{date}_{tweet_id}_{seq}.{ext}"), "file")
                handles = load_handles(
                    handles=data.get("handles"),
                    archive=data.get("archive"),
                    top=int(data.get("top", 0) or 0),
                    offset=int(data.get("offset", 0) or 0),
                )
            except ValueError as exc:
                return self._json({"error": str(exc)}, 400)
            if not handles:
                return self._json({"error": "no accounts selected"}, 400)
            cfg = {
                "handles": handles,
                "posts": int(data.get("posts", 20) or 0),
                "media_types": data.get("media_types", "all"),
                "dir_template": data.get("dir_template", "{handle}"),
                "file_template": data.get("file_template", "{handle}_{date}_{tweet_id}_{seq}.{ext}"),
                "seq_width": int(data.get("seq_width", 2) or 2),
                "out_dir": data.get("out_dir") or DEFAULT_OUT,
                "tz_offset": int(data.get("tz_offset", 8) or 0) if str(data.get("tz_offset", "8")).lstrip("-").isdigit() else 8,
                "max_mb": int(data.get("max_mb", 0) or 0),
                "dry_run": bool(data.get("dry_run", False)),
            }
            jid = _new_id()
            job = {"id": jid, "status": "running", "done_users": 0,
                   "total_users": len(handles), "current": "", "error": "",
                   "summary": {}, "events": [], "created_at": int(time.time())}
            with _lock:
                _jobs[jid] = job

            def progress(ev):
                with _lock:
                    job["events"].append(ev)
                    if ev.get("phase") == "user-done":
                        job["done_users"] = ev.get("user", job["done_users"])
                        job["current"] = ev.get("handle", "")
                    if ev.get("phase") == "file":
                        job["current"] = f"@{ev.get('handle')} {ev.get('file')}"

            def worker():
                try:
                    job["summary"] = run(cfg, progress=progress)
                    job["status"] = "done"
                except Exception as exc:  # noqa: BLE001
                    job["status"] = "error"
                    job["error"] = str(exc)

            threading.Thread(target=worker, daemon=True).start()
            return self._json({"id": jid, "total_users": len(handles)})
        return self._json({"error": "not found"}, 404)

    def log_message(self, *args):  # quieter logs
        pass


def serve(port=8765):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"x-media-grabber API + demo page at http://127.0.0.1:{port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    import sys
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8765)
