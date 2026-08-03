#!/usr/bin/env python3
"""Split verse_discovery.json into per-chapter shards.

The reader loaded one 14.5MB file before it could open a verse panel, so the
first tap on a verse waited ~3.4s over a real network — against a product whose
whole claim is meaning one tap away. Served from localhost this was invisible.

Output mirrors library/translations/, which already works this way:

    library/discovery/<chapter_id>.json
    { "3": [entry, ...], "7": [entry, ...] }

Keyed by verse number within the chapter, so the reader fetches a few KB for
the chapter in front of the person instead of the whole corpus.

Usage:
    python3 scripts/shard_verse_discovery.py [--check]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "library" / "verse_discovery.json"
TOC = ROOT / "library" / "toc.json"
OUT = ROOT / "library" / "discovery"


def chapter_ids_by_label():
    """'Ezra 1' -> 'ezra_1', straight from the library's own table of contents."""
    items = json.loads(TOC.read_text())
    book = None
    out = {}
    for item in items:
        if item.get("type") == "book":
            book = item["label"]
        elif item.get("type") == "chapter" and book:
            out[f"{book} {item['label']}"] = item["id"]
    # The discovery corpus cites sections as "D&C 100"; the table of contents
    # spells the book "Doctrine & Covenants". Without this alias 3,384 refs
    # silently fail to resolve and their study material disappears.
    for label, cid in list(out.items()):
        if label.startswith("Doctrine & Covenants "):
            out["D&C " + label.split(" ", 3)[-1]] = cid
    return out


def main():
    check_only = "--check" in sys.argv
    by_label = chapter_ids_by_label()
    data = json.loads(SOURCE.read_text())

    shards = defaultdict(dict)
    unresolved = []
    entries = 0
    for ref, items in data.items():
        if ":" not in ref:
            unresolved.append(ref)
            continue
        chapter_ref, verse = ref.rsplit(":", 1)
        cid = by_label.get(chapter_ref)
        if not cid:
            unresolved.append(ref)
            continue
        shards[cid][verse] = items
        entries += len(items)

    total = sum(len(json.dumps(v)) for v in shards.values())
    print(f"refs: {len(data)}  entries: {entries}")
    print(f"chapters: {len(shards)}  unresolved refs: {len(unresolved)}")
    if unresolved:
        print("  e.g. " + ", ".join(unresolved[:5]))
    print(f"source: {SOURCE.stat().st_size / 1048576:.1f}MB")
    print(f"shards: {total / 1048576:.1f}MB total, {total / max(len(shards), 1) / 1024:.1f}kB average")

    if check_only:
        return 0

    OUT.mkdir(exist_ok=True)
    for cid, verses in shards.items():
        ordered = {k: verses[k] for k in sorted(verses, key=lambda x: int(x) if x.isdigit() else 0)}
        (OUT / f"{cid}.json").write_text(
            json.dumps(ordered, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
    print(f"wrote {len(shards)} files to {OUT}")

    # Every ref in the original must be findable in exactly one shard.
    recovered = sum(len(json.loads((OUT / f"{c}.json").read_text())) for c in shards)
    print(f"verification: {recovered} verse keys across shards, {len(data) - len(unresolved)} expected")
    return 0 if recovered == len(data) - len(unresolved) else 2


if __name__ == "__main__":
    sys.exit(main())
