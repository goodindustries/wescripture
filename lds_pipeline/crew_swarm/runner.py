#!/usr/bin/env python3
"""
Run Crew swarm on the next pending task from diagnostics/crew_events.jsonl.

  python3 lds_pipeline/crew_swarm/runner.py --once
  python3 lds_pipeline/crew_swarm/runner.py --loop --sleep 30
  python3 lds_pipeline/crew_swarm/runner.py --seed "Ch genesis_1: add entity span annotations"

Env:
  CREW_OLLAMA_BASE_URL   default http://127.0.0.1:11434 (Ollama root; /v1 stripped if present)
  CREW_OLLAMA_MODEL      default qwen2.5:1.5b
Requires Python 3.10+ and: pip install -r requirements-crew.txt
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))

from crew_swarm.events import enqueue_task, load_events, next_pending  # noqa: E402
from crew_swarm.swarm import run_swarm_on_task  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="CrewAI swarm runner for wescripture.")
    ap.add_argument("--once", action="store_true", help="Process one pending task then exit")
    ap.add_argument("--loop", action="store_true", help="Poll for pending tasks forever")
    ap.add_argument("--sleep", type=float, default=30.0, help="Seconds between loop iterations")
    ap.add_argument("--seed", type=str, default="", help="Enqueue one task with this title then exit")
    ap.add_argument("--quiet", action="store_true", help="Less crew verbose logging")
    args = ap.parse_args()

    if args.seed:
        tid = enqueue_task(args.seed, notes="")
        print(f"queued {tid}", flush=True)
        return

    def cycle() -> bool:
        task = next_pending()
        if not task:
            print("no pending tasks", flush=True)
            return False
        print(f"running swarm for {task.get('task_id')} {task.get('title', '')[:80]}", flush=True)
        out = run_swarm_on_task(task, verbose=not args.quiet)
        print(out, flush=True)
        return True

    if args.once:
        cycle()
        return

    if args.loop:
        while True:
            cycle()
            time.sleep(max(5.0, args.sleep))
        return

    # default: once
    cycle()


if __name__ == "__main__":
    main()
