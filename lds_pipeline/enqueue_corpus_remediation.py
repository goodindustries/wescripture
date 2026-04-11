#!/usr/bin/env python3
"""
Queue ledger tasks for corpus + vectorization gaps (dispatch-handled titles).

Reads lds_pipeline/reports/corpus_resource_map.json if present; always checks
catalog and correlation dir on disk.

  python3 lds_pipeline/enqueue_corpus_remediation.py        # print plan only
  python3 lds_pipeline/enqueue_corpus_remediation.py --apply
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPORT = REPO / "lds_pipeline" / "reports" / "corpus_resource_map.json"
LEDGER = REPO / "task-ledger.jsonl"
CACHE = REPO / "lds_pipeline" / "cache"
CATALOG_SW = CACHE / "standard_works" / "verse_catalog.json"
CATALOG_PRIMARY = CACHE / "verse_catalog.json"
CORR = CACHE / "correlations"


def active_titles() -> set[str]:
    """Titles already pending or claimed (avoid duplicate queue)."""
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "lds_pipeline" / "task_ledger.py"),
            "list",
            "--status",
            "pending",
            "claimed",
            "--format",
            "json",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return set()
    try:
        rows = json.loads(r.stdout)
    except json.JSONDecodeError:
        return set()
    return {(t.get("title") or "").strip() for t in rows if t.get("title")}


def plan_tasks(maintenance_only: bool = False) -> list[tuple[str, str]]:
    """Return list of (title, notes)."""
    tasks: list[tuple[str, str]] = []
    cat_ok = CATALOG_PRIMARY.is_file() or CATALOG_SW.is_file()
    n_corr = sum(1 for _ in CORR.glob("*.json")) if CORR.is_dir() else 0
    if maintenance_only:
        cat_ok = True
        n_corr = 999999
    # Fast hygiene first so dispatch workers finish quick tasks before correlate.
    tasks.append(
        (
            "Corpus maintenance: lint_source_paras",
            "Reports HTML missing p.source-para; stderr lists issues",
        )
    )
    tasks.append(
        (
            "Corpus maintenance: add_para_ids_to_sources",
            "Assigns pN ids to source-para; refreshes source_toc paragraph counts",
        )
    )
    if not cat_ok:
        tasks.append(
            (
                "Corpus pipeline: run correlate_embeddings after sync",
                "Runs sync_standard_works.py then correlate_embeddings.py",
            )
        )
    elif n_corr < 100:
        tasks.append(
            (
                "Corpus pipeline: run correlate_embeddings",
                "Dense embeddings + per-verse correlation JSON under lds_pipeline/cache/correlations/",
            )
        )
    return tasks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Append tasks to task-ledger.jsonl")
    ap.add_argument(
        "--maintenance-only",
        action="store_true",
        help="Skip sync/correlate; only lint + add_para_ids (for quick hygiene passes)",
    )
    args = ap.parse_args()

    active = active_titles()
    to_add = []
    for title, notes in plan_tasks(maintenance_only=args.maintenance_only):
        if title in active:
            print(f"skip (already queued): {title}")
            continue
        to_add.append((title, notes))

    for title, notes in to_add:
        print(f"QUEUE: {title}")
        if notes:
            print(f"       {notes[:120]}")
    if not args.apply:
        print("\n(dry-run) pass --apply to append to task-ledger.jsonl")
        return

    for title, notes in to_add:
        r = subprocess.run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "task_ledger.py"),
                "append",
                "--type",
                "queue",
                "--title",
                title,
                "--notes",
                notes,
            ],
            cwd=str(REPO),
        )
        if r.returncode != 0:
            sys.exit(r.returncode)
    print(f"Appended {len(to_add)} task(s).")


if __name__ == "__main__":
    main()
