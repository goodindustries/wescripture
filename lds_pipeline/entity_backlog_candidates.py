#!/usr/bin/env python3
"""List people entities that look incomplete for backfill tranches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PEOPLE = REPO / "library" / "entities" / "people.json"
PEOPLE_IX = REPO / "library" / "entities" / "people_index.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    people = json.loads(PEOPLE.read_text(encoding="utf-8"))
    indexed = set(json.loads(PEOPLE_IX.read_text(encoding="utf-8")).values())

    bad = []
    for row in people:
        eid = row.get("id", "")
        if eid not in indexed:
            continue
        refs = row.get("scripture_refs") or row.get("related_scriptures")
        if not row.get("christ_connection") or not refs:
            bad.append(eid)

    for eid in bad[: args.limit]:
        print(eid)
    print(f"# total candidates: {len(bad)} (showing {min(args.limit, len(bad))})")


if __name__ == "__main__":
    main()
