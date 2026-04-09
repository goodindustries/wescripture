#!/usr/bin/env python3
"""
autonomous_runner.py
====================
Long-running loop: pull, refill the ledger when pending work is low, then run
task_worker (hybrid backend by default).

Designed for a machine with git credentials, Ollama (followup + christ gen), and
optional Claude CLI for tasks dispatch cannot handle.

    python3 lds_pipeline/autonomous_runner.py
    python3 lds_pipeline/autonomous_runner.py --min-pending 12 --scout-max 45
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def count_pending() -> int:
    from task_ledger import _load_events, _project

    tasks = _project(_load_events())
    return sum(1 for t in tasks.values() if t.get("status") == "pending")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-pending", type=int, default=10, help="Scout when pending < this")
    ap.add_argument("--scout-max", type=int, default=50, help="Max tasks task_scout appends per refill")
    ap.add_argument("--sleep", type=int, default=25, help="Seconds between iterations")
    ap.add_argument("--agent-prefix", default="Auto", help="Worker agent name prefix")
    ap.add_argument("--no-scout", action="store_true", help="Never run task_scout")
    ap.add_argument("--worker-backend", default="hybrid", choices=("hybrid", "dispatch", "claude"))
    ap.add_argument("--once", action="store_true", help="Single iteration then exit")
    args = ap.parse_args()

    worker_py = REPO / "lds_pipeline" / "task_worker.py"
    scout_py = REPO / "lds_pipeline" / "task_scout.py"

    iteration = 0
    while True:
        iteration += 1
        print(f"\n=== autonomous_runner iteration {iteration} ===", flush=True)
        subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=str(REPO), check=False,
        )

        if not args.no_scout:
            n = count_pending()
            print(f"  pending tasks: {n}", flush=True)
            if n < args.min_pending:
                need = max(args.scout_max, args.min_pending - n + 5)
                print(f"  running task_scout --max {need} …", flush=True)
                subprocess.run(
                    [
                        sys.executable,
                        str(scout_py),
                        "--max",
                        str(need),
                        "--streams",
                        "all",
                        "--push",
                    ],
                    cwd=str(REPO),
                    check=False,
                )

        agent = f"{args.worker_prefix}{iteration % 10000}"
        print(f"  task_worker --backend {args.worker_backend} --agent {agent} …", flush=True)
        subprocess.run(
            [
                sys.executable,
                str(worker_py),
                "--backend",
                args.worker_backend,
                "--agent",
                agent,
            ],
            cwd=str(REPO),
            check=False,
        )

        if args.once:
            break
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
