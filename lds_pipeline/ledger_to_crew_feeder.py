#!/usr/bin/env python3
"""
Bridge: pull small, dispatch-friendly pending tasks from task-ledger.jsonl into
diagnostics/crew_events.jsonl so crew_swarm/runner.py can execute them.

Adds a first line to crew notes: ledger_task_id:T-xxxx (swarm.py mirrors
complete/reopen back to the ledger).

  python3 lds_pipeline/ledger_to_crew_feeder.py           # enqueue one task
  python3 lds_pipeline/ledger_to_crew_feeder.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))

from crew_swarm.events import enqueue_task, load_events, project_tasks as crew_project  # noqa: E402
from task_ledger import _load_events, _project  # noqa: E402

LEDGER = REPO / "task-ledger.jsonl"

# Titles that match task_dispatch handlers (prefix match).
CREW_ELIGIBLE_PREFIXES = (
    "Corpus maintenance:",
    "Corpus audit:",
    "Ch ",
    "Registry Wikipedia",
    "Christ —",
    "People registry:",
    "Things registry:",
)

# Long / heavy jobs — do not auto-feed to Crew loop.
BLOCK_SUBSTRINGS = (
    "Corpus pipeline: run correlate_embeddings",
    "Corpus pipeline: run correlate_embeddings after sync",
)


def _ledger_ids_in_crew_queue() -> set[str]:
    out: set[str] = set()
    evs = load_events()
    tasks = crew_project(evs)
    for t in tasks.values():
        if t.get("status") not in ("pending", "claimed"):
            continue
        notes = t.get("notes") or ""
        m = re.search(r"ledger_task_id:\s*(T-\d+)", notes)
        if m:
            out.add(m.group(1))
    return out


def _eligible(title: str) -> bool:
    if title.startswith("Donaldson"):
        return False
    if title.startswith("Source Scout:"):
        return False
    if any(s in title for s in BLOCK_SUBSTRINGS):
        return False
    return any(title.startswith(p) for p in CREW_ELIGIBLE_PREFIXES)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not LEDGER.is_file():
        print("No task-ledger.jsonl", file=sys.stderr)
        sys.exit(1)

    ledger_tasks = _project(_load_events())
    pending = sorted(
        (t for t in ledger_tasks.values() if t.get("status") == "pending"),
        key=lambda x: x.get("task_id") or "",
    )

    crew_seen = _ledger_ids_in_crew_queue()

    pick = None
    for t in pending:
        tid = t.get("task_id") or ""
        if tid in crew_seen:
            continue
        title = (t.get("title") or "").strip()
        if not _eligible(title):
            continue
        pick = t
        break

    if not pick:
        print("ledger_to_crew_feeder: no eligible pending task to bridge.")
        return

    tid = pick["task_id"]
    title = (pick.get("title") or "").strip()
    orig_notes = (pick.get("notes") or "").strip()
    bridge_notes = f"ledger_task_id:{tid}\n{orig_notes}".strip()

    print(f"Would bridge {tid}: {title[:90]}…")

    if args.dry_run:
        return

    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "lds_pipeline" / "task_ledger.py"),
            "claim",
            "--task-id",
            tid,
            "--agent",
            "LedgerCrewBridge",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        sys.exit(r.returncode)

    cid = enqueue_task(title=title, notes=bridge_notes, source="ledger_to_crew_feeder")
    print(f"Claimed {tid} → queued {cid} for crew_swarm.")


if __name__ == "__main__":
    main()
