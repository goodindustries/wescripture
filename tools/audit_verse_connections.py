#!/usr/bin/env python3
"""
Audit verse→corpus connection coverage.

Reads `library/verse_discovery.json` and prints:
- verse count
- % with connections
- distribution of connections per verse
- counts by source / collection / tradition_pair

Run from repo root:
    python3 tools/audit_verse_connections.py
"""

import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERSE_DISCOVERY = REPO / "library" / "verse_discovery.json"


def main() -> None:
    if not VERSE_DISCOVERY.exists():
        raise SystemExit(f"Missing {VERSE_DISCOVERY}")

    data = json.loads(VERSE_DISCOVERY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("verse_discovery.json expected object at top level")

    verse_count = len(data)
    with_any = 0
    per_verse = Counter()
    by_source = Counter()
    by_collection = Counter()
    by_pair = Counter()

    for _, entries in data.items():
        n = len(entries or [])
        per_verse[n] += 1
        if n:
            with_any += 1
        for e in entries or []:
            src = str(e.get("source", "") or "")
            coll = str(e.get("collection", "") or "") or src
            pair = str(e.get("tradition_pair", "") or "")
            if src:
                by_source[src] += 1
            if coll:
                by_collection[coll] += 1
            if pair:
                by_pair[pair] += 1

    pct = (with_any / verse_count * 100.0) if verse_count else 0.0
    print(
        json.dumps(
            {
                "verses": verse_count,
                "verses_with_any": with_any,
                "pct_with_any": round(pct, 2),
                "connections_total": sum(by_source.values()),
                "connections_by_source_top": by_source.most_common(20),
                "connections_by_collection_top": by_collection.most_common(20),
                "connections_by_tradition_pair": by_pair.most_common(),
                "per_verse_connection_count_histogram": dict(
                    sorted(per_verse.items(), key=lambda x: x[0])
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Audit verse→corpus connection coverage.

Reads `library/verse_discovery.json` and prints:
- verse count
- % with connections
- distribution of connections per verse
- counts by source / collection / tradition_pair

Run from repo root:
    python3 tools/audit_verse_connections.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
VERSE_DISCOVERY = REPO / "library" / "verse_discovery.json"


def main() -> None:
    if not VERSE_DISCOVERY.exists():
        raise SystemExit(f"Missing {VERSE_DISCOVERY}")

    data = json.loads(VERSE_DISCOVERY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("verse_discovery.json expected object at top level")

    verse_count = len(data)
    with_any = 0
    per_verse = Counter()
    by_source = Counter()
    by_collection = Counter()
    by_pair = Counter()

    for _, entries in data.items():
        n = len(entries or [])
        per_verse[n] += 1
        if n:
            with_any += 1
        for e in entries or []:
            src = str(e.get("source", "") or "")
            coll = str(e.get("collection", "") or "") or src
            pair = str(e.get("tradition_pair", "") or "")
            if src:
                by_source[src] += 1
            if coll:
                by_collection[coll] += 1
            if pair:
                by_pair[pair] += 1

    pct = (with_any / verse_count * 100.0) if verse_count else 0.0

    print(
        json.dumps(
            {
                "verses": verse_count,
                "verses_with_any": with_any,
                "pct_with_any": round(pct, 2),
                "connections_total": sum(by_source.values()),
                "connections_by_source_top": by_source.most_common(20),
                "connections_by_collection_top": by_collection.most_common(20),
                "connections_by_tradition_pair": by_pair.most_common(),
                "per_verse_connection_count_histogram": dict(
                    sorted(per_verse.items(), key=lambda x: x[0])
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

