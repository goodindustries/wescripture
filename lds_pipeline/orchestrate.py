#!/usr/bin/env python3
"""
orchestrate.py
==============
Single entrypoint: git pull → optional task_scout refill → waves of parallel
task_worker processes until the pending queue is empty or --max-waves is hit.

Defaults favor local pipelines (dispatch). Override backend for hybrid/Claude.

  python3 lds_pipeline/orchestrate.py
  python3 lds_pipeline/orchestrate.py --backend hybrid --wave-size 8 --max-waves 30
  python3 lds_pipeline/orchestrate.py --no-scout --once
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))
from task_ledger import _load_events, _project  # noqa: E402

from orchestrate_hints import (  # noqa: E402
    format_claim_report,
    site_base,
    ui_hints_for_task_title,
)


def pending_count() -> int:
    return sum(1 for t in _project(_load_events()).values() if t.get("status") == "pending")


def log_verbose_queue_state(log, prefix: str = "") -> None:
    """Pending + claimed tasks with UI test URLs (deployed site)."""
    tasks = _project(_load_events())
    base = site_base()
    log(f"{prefix}Public site base: {base} (override: WESCRIPTURE_SITE_URL)")
    pending = [t for t in tasks.values() if t.get("status") == "pending"]
    pending.sort(key=lambda x: x.get("task_id") or "")
    claimed = [t for t in tasks.values() if t.get("status") == "claimed"]
    claimed.sort(key=lambda x: x.get("claim_ts") or "", reverse=True)
    log(f"{prefix}Pending: {len(pending)}  |  Claimed (in-flight): {len(claimed)}")
    show_p = pending[:14]
    if show_p:
        log(f"{prefix}Next pending (showing {len(show_p)} of {len(pending)}):")
        for t in show_p:
            tid = t.get("task_id", "")
            title = (t.get("title") or "")[:130]
            log(f"{prefix}  {tid}  {title}")
            for line in ui_hints_for_task_title(t.get("title") or ""):
                log(f"{prefix}    → {line}")
    if claimed:
        log(f"{prefix}In-flight claims:")
        for t in claimed[:12]:
            tid = t.get("task_id", "")
            ag = t.get("claimed_by") or "?"
            title = (t.get("title") or "")[:120]
            log(f"{prefix}  {tid}  agent={ag}  {title}")
            for line in ui_hints_for_task_title(t.get("title") or ""):
                log(f"{prefix}    → {line}")


def log_worker_claim_artifacts(log) -> None:
    """Parse diagnostics/task-worker-Worker*.out for last [Worker] claimed lines + hints."""
    text = format_claim_report(REPO / "diagnostics")
    log("Last claim line per worker log (if any):")
    for line in text.split("\n"):
        log(line)


def git_pull(log) -> None:
    r = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    log(f"git pull → {r.returncode}")
    if r.stdout.strip():
        log(r.stdout.strip()[:500])


def main() -> None:
    ap = argparse.ArgumentParser(description="Orchestrate scout + parallel task workers.")
    ap.add_argument(
        "--backend",
        default=os.environ.get("ORCHESTRATE_BACKEND", "dispatch"),
        help="TASK_WORKER_BACKEND for each worker (default: dispatch)",
    )
    ap.add_argument(
        "--wave-size",
        type=int,
        default=int(os.environ.get("ORCHESTRATE_WAVE_SIZE", os.environ.get("MAX_PARALLEL_WORKERS", "8"))),
        help="Workers per wave (default: MAX_PARALLEL_WORKERS or 8)",
    )
    ap.add_argument(
        "--min-pending",
        type=int,
        default=8,
        help="Run task_scout when pending count is below this (unless --no-scout)",
    )
    ap.add_argument("--scout-max", type=int, default=45, help="Upper bound passed to task_scout --max")
    ap.add_argument(
        "--max-waves",
        type=int,
        default=0,
        help="Stop after this many waves (0 = unlimited until queue empty)",
    )
    ap.add_argument("--sleep", type=int, default=20, help="Seconds between waves")
    ap.add_argument("--no-scout", action="store_true", help="Never run task_scout")
    ap.add_argument(
        "--once",
        action="store_true",
        help="Single wave (still pulls; scout runs if pending low unless --no-scout)",
    )
    ap.add_argument("--log", type=Path, default=REPO / "diagnostics" / "orchestrate.log")
    ap.add_argument("--no-dashboard", action="store_true", help="Skip build_dashboard_state.py at exit")
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Skip verbose pending/claim/UI lines in the log",
    )
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    log("=== orchestrate start ===")
    wave = 0
    while True:
        git_pull(log)
        n = pending_count()
        log(f"pending={n}")
        if not args.quiet:
            log_verbose_queue_state(log)

        if not args.no_scout and n < args.min_pending:
            need = max(args.scout_max, args.min_pending - n + 5)
            log(f"task_scout --max {need} --streams all --push")
            subprocess.run(
                [
                    sys.executable,
                    str(REPO / "lds_pipeline" / "task_scout.py"),
                    "--max",
                    str(need),
                    "--streams",
                    "all",
                    "--push",
                ],
                cwd=str(REPO),
                check=False,
            )
            n = pending_count()
            log(f"after scout pending={n}")

        if n == 0:
            log("queue empty — done")
            break

        wave += 1
        if args.max_waves and wave > args.max_waves:
            log(f"stopped: max-waves {args.max_waves}")
            break

        log(f"wave {wave}: {args.wave_size} workers backend={args.backend}")
        log(
            "  (each slot runs task_worker.py once: claims → dispatch/claude → commit; "
            "see diagnostics/task-worker-WorkerNNN.out)"
        )
        env = os.environ.copy()
        env["TASK_WORKER_BACKEND"] = args.backend
        cap = max(args.wave_size, int(env.get("MAX_PARALLEL_WORKERS", "32")))
        env["MAX_PARALLEL_WORKERS"] = str(cap)
        rc = subprocess.run(
            [str(REPO / "lds_pipeline" / "run_parallel_task_workers.sh"), str(args.wave_size)],
            cwd=str(REPO),
            env=env,
            check=False,
        ).returncode
        log(f"wave {wave} worker script exit={rc}; pending now {pending_count()}")
        if not args.quiet:
            log_worker_claim_artifacts(log)
            log_verbose_queue_state(log, prefix="  post-wave ")

        if args.once:
            log("--once: stopping after single wave")
            break

        time.sleep(args.sleep)

    if not args.no_dashboard:
        dash = REPO / "lds_pipeline" / "build_dashboard_state.py"
        if dash.is_file():
            log("running build_dashboard_state.py")
            subprocess.run([sys.executable, str(dash)], cwd=str(REPO), check=False)
            if not args.quiet:
                b = site_base()
                log(f"  Ops dashboard (after deploy): {b}/dashboard.html")
                log(f"  Verse coverage: {b}/verse_coverage.html")

    log("=== orchestrate end ===")


if __name__ == "__main__":
    main()
