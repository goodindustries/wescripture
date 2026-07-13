#!/usr/bin/env python3
"""
Extract verse-level footnotes from verse_discovery.json + source corpus.
Merge with existing donaldson/ commentary into per-chapter JSON files.

Output: library/footnotes/<book>_<chapter>.json
Schema: {verse: {notes: [], quotes: [{text, speaker, source, date, ref, type, attr}, ...]}}
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict


def normalize_verse_ref(verse_str):
    """Convert 'Genesis 1:3' → ('genesis', 1, 3) or None if invalid."""
    match = re.match(r"([A-Za-z0-9\s&]+?)\s+(\d+):(\d+)", verse_str)
    if not match:
        return None
    book = match.group(1).lower().replace(" ", "_").replace("&", "and")
    chapter = int(match.group(2))
    verse = int(match.group(3))
    return (book, chapter, verse)


def load_verse_discovery():
    """Load verse_discovery.json and group by (book, chapter)."""
    with open("library/verse_discovery.json") as f:
        data = json.load(f)

    # Group by (book, chapter)
    grouped = defaultdict(lambda: defaultdict(list))
    for verse_str, entries in data.items():
        parsed = normalize_verse_ref(verse_str)
        if not parsed:
            continue
        book, chapter, verse_num = parsed
        entries_list = entries if isinstance(entries, list) else [entries]
        for entry in entries_list:
            grouped[(book, chapter)][verse_num].append({
                "source": entry.get("source"),
                "source_label": entry.get("source_label"),
                "text": entry.get("source_text"),
                "source_doc_id": entry.get("source_doc_id"),
                "source_para": entry.get("source_para"),
            })

    return grouped


def load_donaldson(book, chapter):
    """Load existing donaldson/<book>_<chapter>.json if it exists."""
    fname = f"library/donaldson/{book}_{chapter}.json"
    if os.path.exists(fname):
        with open(fname) as f:
            return json.load(f)
    return {}


def extract_source_label_parts(source_label):
    """Parse 'Millennial Star: millennial_star_1840_1859' → source_type='Millennial Star'."""
    if ":" in source_label:
        return source_label.split(":")[0].strip()
    return source_label


def merge_verse_footnotes(verse_num, discovery_entries, donaldson_data):
    """Merge verse_discovery entries + donaldson into footnote structure."""
    # Start with existing donaldson
    verse_key = str(verse_num)
    footnote = dict(donaldson_data.get(verse_key, {}))

    # Add discovered sources as quotes
    if discovery_entries:
        if "quotes" not in footnote:
            footnote["quotes"] = []

        for entry in discovery_entries:
            source_type = extract_source_label_parts(entry.get("source_label", "Unknown"))
            quote_obj = {
                "text": entry.get("text", ""),
                "speaker": "",  # No speaker in verse_discovery
                "source": source_type,
                "date": "",
                "ref": "",
                "type": "cross_source",
                "attr": f"{source_type} ({entry.get('source_doc_id', 'unknown')})",
            }
            # Avoid duplicates
            if quote_obj not in footnote["quotes"]:
                footnote["quotes"].append(quote_obj)

    return footnote if footnote else None


def main():
    os.makedirs("library/footnotes", exist_ok=True)

    print("Loading verse_discovery.json...")
    discovery = load_verse_discovery()

    print(f"Processing {len(discovery)} book-chapter combinations...")
    total_verses = 0
    files_written = 0

    for (book, chapter), verses in sorted(discovery.items()):
        # Load existing donaldson
        donaldson = load_donaldson(book, chapter)

        # Merge verse footnotes
        merged = {}
        for verse_num, entries in sorted(verses.items()):
            footnote = merge_verse_footnotes(verse_num, entries, donaldson)
            if footnote:
                merged[str(verse_num)] = footnote
                total_verses += 1

        # Write merged footnotes if there's anything to write
        if merged:
            output_file = f"library/footnotes/{book}_{chapter}.json"
            with open(output_file, "w") as f:
                json.dump(merged, f, indent=2)
            files_written += 1
            print(f"  {book}_{chapter}: {len(merged)} verses")

    print(f"\n✓ Extraction complete: {total_verses} verses across {files_written} files")
    print(f"  Output directory: library/footnotes/")


if __name__ == "__main__":
    main()
