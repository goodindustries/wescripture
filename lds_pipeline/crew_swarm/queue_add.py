#!/usr/bin/env python3
"""
Queue work for the **local Crew runner** (consumer: ``runner.py`` / ``run_crew_swarm_forever.sh``).

Intended callers: **core agent** (Cursor), humans, or automation — anyone who *decides*
what should run. The runner only pulls ``next_pending()`` and executes; it does not
create tasks.

  python3 lds_pipeline/crew_swarm/queue_add.py --title "Ch genesis_1: add entity span annotations"
  python3 lds_pipeline/crew_swarm/queue_add.py --title "..." --notes "MISSION: ..." --source Cursor

Tasks land in ``diagnostics/crew_events.jsonl`` as ``task_queued`` events.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))

from crew_swarm.events import enqueue_task  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Enqueue one task for the local crew runner.")
    ap.add_argument("--title", required=True, help="Task title (must match task_dispatch patterns when possible)")
    ap.add_argument("--notes", default="", help="Optional notes / mission text")
    ap.add_argument(
        "--source",
        default="CoreAgent",
        help="Producer id stored on the event (default: CoreAgent)",
    )
    args = ap.parse_args()
    tid = enqueue_task(args.title, notes=args.notes, source=args.source)
    print(tid, flush=True)


if __name__ == "__main__":
    main()
