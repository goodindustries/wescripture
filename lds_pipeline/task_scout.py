#!/usr/bin/env python3
"""
task_scout.py
=============
Scan the scripture corpus (TOC-driven) and append *task_queued* rows for
chapter-scale gaps: entity spans, notes HTML, Donaldson JSON coverage.

Aligns with MISSION.md — every verse/chapter should deepen connections,
provenance, and the noun-world without dead ends.

Dedupes against **pending** and **claimed** ledger tasks by exact title match.

Run from repo root:
    python3 lds_pipeline/task_scout.py --dry-run
    python3 lds_pipeline/task_scout.py --max 40 --push   # commit+push ledger

Schedule (example): every few hours so workers never run out of scoped work.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from task_ledger import _append, _load_events, _project, _push_ledger, utc_now

REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "library"
TOC_PATH = LIB / "toc.json"
CHAP_DIR = LIB / "chapters"
DON_DIR = LIB / "donaldson"


def load_chapter_ids() -> list[str]:
    toc = json.loads(TOC_PATH.read_text(encoding="utf-8"))
    return [e["id"] for e in toc if e.get("type") == "chapter" and e.get("id")]


def chapter_html_has_word_spans(text: str) -> bool:
    return 'class="w"' in text or "class='w'" in text


def chapter_html_needs_entity_attrs(text: str) -> bool:
    if not chapter_html_has_word_spans(text):
        return False
    return (
        "data-entity" not in text
        and "data-place" not in text
        and "data-thing" not in text
    )


def open_task_titles() -> set[str]:
    tasks = _project(_load_events())
    return {
        t["title"]
        for t in tasks.values()
        if t.get("status") in ("pending", "claimed") and t.get("title")
    }


def next_task_ids_start() -> int:
    events = _load_events()
    nums = [
        int(t[2:])
        for t in {e.get("task_id") for e in events}
        if isinstance(t, str) and t.startswith("T-") and t[2:].isdigit()
    ]
    return (max(nums) + 1) if nums else 1


def collect_entity_span_tasks(chapter_ids: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for cid in chapter_ids:
        path = CHAP_DIR / f"{cid}.html"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not chapter_html_needs_entity_attrs(text):
            continue
        title = f"Ch {cid}: add entity span annotations (data-entity / place / thing)"
        notes = (
            "MISSION: discovery panel chips for people/places/things. "
            "Run from repo root: python3 lds_pipeline/annotate_entity_spans.py "
            f"(scope this chapter: --books pattern matching {cid}). "
            "Match rules in annotate_entity_spans.py / AGENT_GUIDELINES.md §4."
        )
        out.append((title, notes))
    return out


def collect_notes_tasks(chapter_ids: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for cid in chapter_ids:
        if (CHAP_DIR / f"{cid}_notes.html").is_file():
            continue
        title = f"Ch {cid}: add or repair _notes.html (commentary / semantic panel)"
        notes = (
            "MISSION: reader should see commentary and cross-corpus quotes for this chapter. "
            f"Expected path library/chapters/{cid}_notes.html — follow existing *_notes.html structure."
        )
        out.append((title, notes))
    return out


def collect_donaldson_tasks(chapter_ids: list[str]) -> list[tuple[str, str]]:
    don = {p.stem for p in DON_DIR.glob("*.json")}
    ch_set = set(chapter_ids)
    missing = sorted(ch_set - don)
    by_book: dict[str, list[str]] = defaultdict(list)
    for cid in missing:
        m = re.match(r"^(.+)_(\d+)$", cid)
        book = m.group(1) if m else cid
        by_book[book].append(cid)

    out: list[tuple[str, str]] = []
    for book, slugs in sorted(by_book.items(), key=lambda x: (-len(x[1]), x[0])):
        n = len(slugs)
        title = f"Donaldson — {book}: add commentary JSON for {n} missing chapter(s)"
        sample = ", ".join(slugs[:15])
        if len(slugs) > 15:
            sample += ", …"
        notes = (
            f"MISSION: Donaldson notes feed verse-level insight. Missing chapter ids: {sample}. "
            "Output: library/donaldson/{slug}.json aligned with existing schema in sibling files."
        )
        out.append((title, notes))
    return out


def round_robin_take(
    queues: list[list[tuple[str, str]]],
    titles_used: set[str],
    max_tasks: int,
) -> list[tuple[str, str]]:
    """Interleave streams so one run spreads work across entity / notes / Donaldson."""
    picked: list[tuple[str, str]] = []
    indices = [0] * len(queues)
    while len(picked) < max_tasks:
        progressed = False
        for qi, q in enumerate(queues):
            while indices[qi] < len(q):
                title, notes = q[indices[qi]]
                indices[qi] += 1
                if title in titles_used:
                    continue
                picked.append((title, notes))
                titles_used.add(title)
                progressed = True
                break
            if len(picked) >= max_tasks:
                break
        if not progressed:
            break
    return picked


def main() -> None:
    ap = argparse.ArgumentParser(description="Queue chapter-scoped tasks from corpus gaps.")
    ap.add_argument("--max", type=int, default=30, help="Max new tasks to append this run")
    ap.add_argument("--dry-run", action="store_true", help="Print only; do not write ledger")
    ap.add_argument(
        "--push",
        action="store_true",
        help="After appending, git commit + push task-ledger.jsonl (same as task_ledger append --push)",
    )
    ap.add_argument(
        "--streams",
        default="entity,notes,donaldson",
        help="Comma list: entity, notes, donaldson (default: all three)",
    )
    args = ap.parse_args()

    if not TOC_PATH.is_file():
        print("ERROR: library/toc.json missing", file=sys.stderr)
        sys.exit(1)

    streams = {s.strip().lower() for s in args.streams.split(",") if s.strip()}
    chapter_ids = load_chapter_ids()

    queues: list[list[tuple[str, str]]] = []
    if "entity" in streams:
        queues.append(collect_entity_span_tasks(chapter_ids))
    if "notes" in streams:
        queues.append(collect_notes_tasks(chapter_ids))
    if "donaldson" in streams:
        queues.append(collect_donaldson_tasks(chapter_ids))

    open_titles = open_task_titles()
    candidates = round_robin_take(queues, set(open_titles), args.max)

    if not candidates:
        print("task_scout: no new tasks (queues empty or all titles already open).")
        return

    print(f"task_scout: appending {len(candidates)} task(s) (dry_run={args.dry_run})")
    for title, _ in candidates[:15]:
        print(f"  • {title[:100]}{'…' if len(title) > 100 else ''}")
    if len(candidates) > 15:
        print(f"  … +{len(candidates) - 15} more")

    if args.dry_run:
        return

    seq = next_task_ids_start()
    for title, notes in candidates:
        entry = {
            "ts": utc_now(),
            "event": "task_queued",
            "task_id": f"T-{seq:04d}",
            "title": title,
            "notes": notes,
        }
        _append(entry)
        seq += 1

    if args.push:
        _push_ledger()
    else:
        print("task_scout: ledger updated locally — commit/push or rerun with --push")


if __name__ == "__main__":
    main()
