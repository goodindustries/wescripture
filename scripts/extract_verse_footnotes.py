#!/usr/bin/env python3
"""
Extract verse-level footnotes from verse_discovery.json + source corpus.
Merge with existing donaldson/ commentary into per-chapter JSON files.

Quality fixes:
- Merge orphaned citation tails into preceding note
- Drop mid-sentence fragments (start lowercase, end mid-word)
- Remove verse-text leakage (notes matching verse content)
- Extract inline citations into structured fields

Output: library/footnotes/<book>_<chapter>.json
Schema: {verse: {notes: [], quotes: [{text, speaker, source, date, ref, type, attr, src}, ...]}}
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher


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


def is_citation_fragment(text):
    """Check if text is a citation fragment (orphaned tail)."""
    if not text:
        return False
    # Starts with lowercase OR citation pattern
    if text[0].islower():
        return True
    if re.match(r"^(or |and |see |cf\. |Bednar|Ensign|Conference Report)", text):
        return True
    if re.match(r"^\([A-Z][a-z]+,", text):  # (Author, ...
        return True
    return False


def text_similarity(a, b):
    """Return similarity ratio (0-1) between two strings."""
    if not a or not b:
        return 0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def is_verse_text_leak(note_text, verse_text):
    """Check if note is the actual verse text (circular garbage)."""
    if not note_text or not verse_text:
        return False
    # If note is ≥80% similar to verse, it's a leak
    return text_similarity(note_text, verse_text) > 0.8


def extract_inline_citation(text):
    """Extract structured citation from inline text. Returns (text, src_dict) or (text, None)."""
    if not text:
        return text, None

    # Match patterns like "(Author, Work, Date, p.N)" at end
    citation_match = re.search(r'\(([^)]+?),\s*(?:pp?\.?\s*)?(\d+)\)', text)
    if citation_match:
        citation_text = citation_match.group(0)
        cleaned_text = text[:citation_match.start()].rstrip()
        author_work = citation_match.group(1)
        page = citation_match.group(2)

        return cleaned_text, {
            "citation": citation_text,
            "author_work": author_work,
            "page": page
        }

    return text, None


def clean_and_merge_notes(notes_list, verse_text):
    """
    Clean note list: merge fragments, drop truncations, remove verse leaks.
    Returns cleaned list.
    """
    if not notes_list:
        return []

    cleaned = []
    for note in notes_list:
        if not note or not isinstance(note, str):
            continue

        note = note.strip()
        if not note:
            continue

        # Drop verse-text leaks
        if is_verse_text_leak(note, verse_text):
            continue

        # Drop fragments <40 chars after cleaning
        if len(note) < 40:
            continue

        # Extract inline citation if present
        note_text, citation_src = extract_inline_citation(note)

        # Merge fragments into previous note if this one starts lowercase
        if is_citation_fragment(note_text):
            if cleaned:
                # Merge into previous
                cleaned[-1] = cleaned[-1] + " " + note_text
            continue

        cleaned.append(note_text)

    return cleaned


def merge_verse_footnotes(verse_num, discovery_entries, donaldson_data, verse_text=""):
    """Merge verse_discovery entries + donaldson into footnote structure."""
    # Start with existing donaldson
    verse_key = str(verse_num)
    footnote = dict(donaldson_data.get(verse_key, {}))

    # Clean existing notes
    if "notes" in footnote:
        footnote["notes"] = clean_and_merge_notes(footnote["notes"], verse_text)
        if not footnote["notes"]:
            del footnote["notes"]

    # Add discovered sources as quotes
    if discovery_entries:
        if "quotes" not in footnote:
            footnote["quotes"] = []

        for entry in discovery_entries:
            text = entry.get("text", "").strip()

            # Skip verse leaks
            if is_verse_text_leak(text, verse_text):
                continue

            # Skip short fragments
            if len(text) < 40:
                continue

            source_type = extract_source_label_parts(entry.get("source_label", "Unknown"))

            # Extract structured citation
            text, citation_src = extract_inline_citation(text)

            quote_obj = {
                "text": text,
                "speaker": "",  # No speaker in verse_discovery
                "source": source_type,
                "date": "",
                "ref": "",
                "type": "cross_source",
                "attr": f"{source_type} ({entry.get('source_doc_id', 'unknown')})",
            }

            # Add structured citation if found
            if citation_src:
                quote_obj["src"] = citation_src

            # Avoid duplicates
            if quote_obj not in footnote["quotes"]:
                footnote["quotes"].append(quote_obj)

    return footnote if footnote else None


def load_chapter_verses(book, chapter):
    """Load verse text from HTML file. Returns {verse_num: verse_text, ...}."""
    html_file = f"library/chapters/{book}_{chapter}.html"
    verses = {}

    if not os.path.exists(html_file):
        return verses

    try:
        with open(html_file, encoding='utf-8') as f:
            content = f.read()
            # Extract verse text from <span class="verse-text">...</span>
            verse_matches = re.findall(r'<span class="verse-text">([^<]+)</span>', content)
            # Also match verse numbers: <span class="verse-num">(\d+)</span>
            verse_nums = re.findall(r'<span class="verse-num">(\d+)</span>', content)

            for vnum, vtext in zip(verse_nums, verse_matches):
                try:
                    verses[int(vnum)] = vtext.strip()
                except ValueError:
                    pass
    except Exception as e:
        pass  # If HTML parsing fails, just skip verse-leak detection

    return verses


def main():
    os.makedirs("library/footnotes", exist_ok=True)

    print("Loading verse_discovery.json...")
    discovery = load_verse_discovery()

    print(f"Processing {len(discovery)} book-chapter combinations...")
    total_verses = 0
    files_written = 0
    defects_dropped = 0

    for (book, chapter), verses in sorted(discovery.items()):
        # Load existing donaldson
        donaldson = load_donaldson(book, chapter)

        # Load chapter text for verse-leak detection
        chapter_verses = load_chapter_verses(book, chapter)

        # Merge verse footnotes
        merged = {}
        for verse_num, entries in sorted(verses.items()):
            verse_text = chapter_verses.get(verse_num, "")
            footnote = merge_verse_footnotes(verse_num, entries, donaldson, verse_text)
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
