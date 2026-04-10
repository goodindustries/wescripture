#!/usr/bin/env python3
"""
Local-only HTTP UI for starting/stopping agents and viewing ledger + process state.

  python3 lds_pipeline/agent_ui_server.py
  # open http://127.0.0.1:8765/

Binds 127.0.0.1 only. Set AGENT_UI_PORT to change port.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))
from task_ledger import _load_events, _project  # noqa: E402

DIAG = REPO / "diagnostics"
FEED = DIAG / "track.feed.txt"
PAUSE_SH = REPO / "lds_pipeline" / "pause_agents.sh"
FOREVER_SH = REPO / "lds_pipeline" / "run_orchestrate_forever.sh"
HTML_PATH = Path(__file__).resolve().parent / "agent_ui.html"
ORCH_RUN_LOG = DIAG / "orchestrate-run.out"

def _feed_rel() -> str:
    try:
        return str(FEED.relative_to(REPO))
    except ValueError:
        return str(FEED)


PGREP_PATTERNS = (
    "orchestrate.py",
    "run_orchestrate_forever",
    "task_worker.py",
    "track_feed.py",
)


def _pgrep_count(pattern: str) -> int:
    try:
        r = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=4,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return 0
        return len([x for x in r.stdout.strip().splitlines() if x.strip()])
    except (OSError, subprocess.TimeoutExpired):
        return 0


def _forever_running() -> bool:
    return _pgrep_count("run_orchestrate_forever") > 0


def collect_state() -> dict:
    tasks = _project(_load_events())
    c = Counter(t.get("status") for t in tasks.values())
    feed_tail: list[str] = []
    if FEED.is_file():
        lines = FEED.read_text(encoding="utf-8", errors="replace").splitlines()
        feed_tail = lines[-24:]

    procs = {p: _pgrep_count(p) for p in PGREP_PATTERNS}
    return {
        "time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "ledger": {
            "pending": c.get("pending", 0),
            "claimed": c.get("claimed", 0),
            "completed": c.get("completed", 0),
        },
        "processes": procs,
        "forever_running": _forever_running(),
        "feed_path": _feed_rel(),
        "feed_tail": feed_tail,
    }


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    n = int(handler.headers.get("Content-Length", "0") or "0")
    if n <= 0:
        return b""
    return handler.rfile.read(n)


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentUI/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def _json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            try:
                self._json(200, collect_state())
            except Exception as e:  # noqa: BLE001
                self._json(500, {"error": str(e)})
            return
        if path in ("/", "/index.html"):
            if not HTML_PATH.is_file():
                self._json(500, {"error": f"missing {HTML_PATH}"})
                return
            self._html(200, HTML_PATH.read_bytes())
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        _read_body(self)

        if path == "/api/stop":
            if not PAUSE_SH.is_file():
                self._json(500, {"ok": False, "error": f"missing {PAUSE_SH}"})
                return
            try:
                r = subprocess.run(
                    ["/bin/bash", str(PAUSE_SH)],
                    cwd=str(REPO),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                msg = "Stop issued (pause_agents.sh)."
                if r.stdout:
                    msg += "\n" + r.stdout.strip()[:800]
                if r.returncode != 0 and r.stderr:
                    msg += "\n" + r.stderr.strip()[:400]
                self._json(200, {"ok": True, "message": msg})
            except Exception as e:  # noqa: BLE001
                self._json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/start":
            if not FOREVER_SH.is_file():
                self._json(500, {"ok": False, "error": f"missing {FOREVER_SH}"})
                return
            if _forever_running():
                self._json(200, {"ok": True, "message": "Already running (run_orchestrate_forever)."})
                return
            DIAG.mkdir(parents=True, exist_ok=True)
            log_f = ORCH_RUN_LOG.open("a", encoding="utf-8")
            try:
                log_f.write(
                    f"\n--- agent_ui start {datetime.now(timezone.utc).isoformat()} ---\n"
                )
                log_f.flush()
                subprocess.Popen(
                    ["/bin/bash", str(FOREVER_SH)],
                    cwd=str(REPO),
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            except Exception as e:  # noqa: BLE001
                log_f.close()
                self._json(500, {"ok": False, "error": str(e)})
                return
            self._json(
                200,
                {
                    "ok": True,
                    "message": "Started run_orchestrate_forever.sh (logs → diagnostics/orchestrate-run.out).",
                },
            )
            return

        self.send_error(404)


def main() -> None:
    host = os.environ.get("AGENT_UI_BIND", "127.0.0.1")
    port = int(os.environ.get("AGENT_UI_PORT", "8765"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Agent UI  http://{host}:{port}/  (Ctrl+C to stop)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)


if __name__ == "__main__":
    main()
