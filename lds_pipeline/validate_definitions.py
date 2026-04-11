#!/usr/bin/env python3
"""Offline check: verse_discovery entries missing source_doc_id (should be empty)."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VD = REPO / "library" / "verse_discovery.json"


def main() -> None:
    data = json.loads(VD.read_text(encoding="utf-8"))
    bad = []
    for ref, rows in data.items():
        for e in rows:
            if not e.get("source_doc_id"):
                bad.append((ref, e.get("source"), e.get("source_label", "")[:60]))
    if bad:
        print(f"Missing source_doc_id: {len(bad)} (showing up to 12)")
        for row in bad[:12]:
            print(" ", row)
        raise SystemExit(1)
    print("verse_discovery: all entries have source_doc_id OK")


if __name__ == "__main__":
    main()
