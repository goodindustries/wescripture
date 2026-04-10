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
import re
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

from orchestrate_hints import scan_worker_out_logs  # noqa: E402

DIAG = REPO / "diagnostics"
ORCH_LOG = DIAG / "orchestrate.log"
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


def _pgrep_fl_lines(pattern: str) -> list[str]:
    try:
        r = subprocess.run(
            ["pgrep", "-fl", pattern],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0 or not (r.stdout or "").strip():
            return []
        return [x.strip() for x in r.stdout.strip().splitlines() if x.strip()]
    except (OSError, subprocess.TimeoutExpired):
        return []


_AGENT_RE = re.compile(r"--agent\s+(Worker\d+)")


def _task_worker_processes() -> list[dict]:
    """Running task_worker.py PIDs with WorkerNNN from argv."""
    rows: list[dict] = []
    for line in _pgrep_fl_lines("lds_pipeline/task_worker.py"):
        parts = line.split(None, 1)
        pid = parts[0] if parts else ""
        rest = parts[1] if len(parts) > 1 else line
        m = _AGENT_RE.search(rest)
        rows.append(
            {
                "pid": pid,
                "agent": m.group(1) if m else "?",
                "cmdline_tail": rest[-120:] if len(rest) > 120 else rest,
            }
        )
    rows.sort(key=lambda x: x.get("agent") or "")
    return rows


def _wave_cap() -> int:
    return int(
        os.environ.get(
            "ORCHESTRATE_WAVE_SIZE",
            os.environ.get("MAX_PARALLEL_WORKERS", "8"),
        )
    )


def _last_orchestrate_wave_info() -> dict:
    """Best-effort parse of last 'wave N: M workers' from orchestrate.log."""
    out: dict = {"wave_num": None, "workers_requested": None, "line": ""}
    if not ORCH_LOG.is_file():
        return out
    try:
        lines = ORCH_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    wave_re = re.compile(r"wave\s+(\d+):\s+(\d+)\s+workers\s+backend=")
    for line in reversed(lines[-400:]):
        m = wave_re.search(line)
        if m:
            out["wave_num"] = int(m.group(1))
            out["workers_requested"] = int(m.group(2))
            out["line"] = line.strip()[:200]
            break
    return out


def _worker_out_tail(agent: str) -> dict[str, str]:
    path = DIAG / f"task-worker-{agent}.out"
    empty = {"models_line": "", "last_claim_line": "", "activity_line": ""}
    if not path.is_file():
        return empty
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return empty
    chunk = lines[-100:] if len(lines) > 100 else lines
    models_line = ""
    claim_line = ""
    for line in reversed(chunk):
        s = line.strip()
        if not s or s.startswith("==="):
            continue
        if "models:" in s and "backend=" in s:
            models_line = s[:240]
            break
    for line in reversed(chunk):
        s = line.strip()
        if "] claimed " in s and "T-" in s:
            claim_line = s[:240]
            break
    activity_line = ""
    for line in reversed(chunk[-25:]):
        s = line.strip()
        if not s or s.startswith("==="):
            continue
        activity_line = s[:240]
        break
    return {
        "models_line": models_line,
        "last_claim_line": claim_line,
        "activity_line": activity_line,
    }


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
    tw = _task_worker_processes()
    n_run = len(tw)
    cap = _wave_cap()
    ow = _last_orchestrate_wave_info()
    workers_requested = ow.get("workers_requested") or cap
    idle_slots = max(0, int(workers_requested) - n_run)

    ledger_by_agent: dict[str, dict] = {}
    for t in tasks.values():
        if t.get("status") != "claimed":
            continue
        ag = t.get("claimed_by") or ""
        if not ag or not ag.startswith("Worker"):
            continue
        ledger_by_agent[ag] = {
            "task_id": t.get("task_id", ""),
            "title": (t.get("title") or "")[:300],
            "claim_ts": t.get("claim_ts") or "",
        }

    agents_seen: set[str] = {r["agent"] for r in tw if r.get("agent") != "?"}
    agents_seen |= set(ledger_by_agent.keys())
    for row in scan_worker_out_logs(DIAG, tail_lines=400):
        ag = row.get("agent") or ""
        if ag.startswith("Worker"):
            agents_seen.add(ag)
    agents = sorted(a for a in agents_seen if a and a.startswith("Worker"))

    worker_rows: list[dict] = []
    for ag in agents:
        pid = next((r["pid"] for r in tw if r.get("agent") == ag), "")
        st = _worker_out_tail(ag)
        lg = ledger_by_agent.get(ag)
        task_id = lg["task_id"] if lg else ""
        title = lg["title"] if lg else ""
        if not title and st["last_claim_line"]:
            title = st["last_claim_line"][:200]
        phase = "running" if pid else "idle"
        if lg and pid:
            phase = "active"
        elif lg and not pid:
            phase = "claimed (process ended?)"
        worker_rows.append(
            {
                "agent": ag,
                "pid": pid,
                "phase": phase,
                "task_id": task_id,
                "title": title,
                "models_line": st["models_line"],
                "last_claim_line": st["last_claim_line"],
                "activity_line": st["activity_line"],
            }
        )

    def _agent_sort(name: str) -> tuple[int, str]:
        m = re.match(r"Worker(\d+)$", name)
        return (int(m.group(1)), name) if m else (9999, name)

    worker_rows.sort(key=lambda r: _agent_sort(r.get("agent") or ""))

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
        "workers": {
            "running_count": n_run,
            "parallelism_cap_env": cap,
            "last_wave": ow,
            "idle_slots_vs_wave": idle_slots,
            "workers_requested_last_wave": workers_requested,
        },
        "worker_processes": tw,
        "worker_rows": worker_rows,
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
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
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
