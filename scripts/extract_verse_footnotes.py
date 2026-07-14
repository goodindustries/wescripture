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


def extract_source_label_parts(source_label):
    """Parse 'Millennial Star: millennial_star_1840_1859' → source_type='Millennial Star'."""
    if ":" in source_label:
        return source_label.split(":")[0].strip()
    return source_label


_MONTHS = {"january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"}

def normalize_source_citation(source_type, doc_id):
    """Turn an internal doc_id like
      'millennial_star:millennial_star_1840_1859_1852_april_vol_14_no_09'
    into a human citation like 'Millennial Star, April 1852 (Vol. 14, No. 9)'
    instead of exposing the raw slug to readers.
    """
    slug = doc_id.split(":", 1)[1] if ":" in doc_id else doc_id

    # Periodical pattern: ..._<year>_<month>_vol_<N>_no_<NN>
    m = re.search(r"(\d{4})_([a-z]+)_vol_0*(\d+)_no_0*(\d+)$", slug)
    if m and m.group(2) in _MONTHS:
        year, month, vol, no = m.groups()
        return f"{source_type}, {month.capitalize()} {year} (Vol. {vol}, No. {no})"

    # General Conference pattern: general_conference_<year>_<month#>_<title-slug>
    m = re.search(r"(\d{4})_(\d{1,2})_(.+)$", slug)
    if m and source_type == "General Conference":
        year, month_num, title_slug = m.groups()
        try:
            month_name = ["January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November",
                          "December"][int(month_num) - 1]
        except (ValueError, IndexError):
            month_name = month_num
        title = title_slug.replace("_", " ").strip().title()
        return f"{source_type}, {month_name} {year} — {title}"

    # Volume-only pattern: vol_13 / vol1
    m = re.match(r"vol_?0*(\d+)$", slug)
    if m:
        return f"{source_type}, Vol. {m.group(1)}"

    # Generic fallback: humanize the slug, dropping a leading repeat of the
    # source name itself (e.g. "millennial_star_1840_1859..." under source
    # "millennial_star").
    cleaned = slug
    src_prefix = doc_id.split(":", 1)[0] if ":" in doc_id else ""
    if src_prefix and cleaned.startswith(src_prefix + "_"):
        cleaned = cleaned[len(src_prefix) + 1:]
    cleaned = cleaned.replace("_", " ").strip()
    if not cleaned:
        return source_type
    return f"{source_type} — {cleaned.title()}"


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


def merge_verse_footnotes(verse_num, discovery_entries, verse_text=""):
    """Build footnote structure from newly-discovered cross_source quotes only.

    The reader loads library/donaldson/ and library/footnotes/ separately and
    concatenates their `quotes` arrays at render time (ensureDonaldsonLoaded in
    library/index.html). Seeding this output from donaldson_data's own
    notes/quotes used to duplicate every Donaldson quote onto itself once
    merged client-side (fixed in 94eae596a, then reintroduced by re-running
    this script without this note — don't seed from donaldson_data again).
    """
    footnote = {}

    # Add discovered sources as quotes
    if discovery_entries:
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

            doc_id = entry.get("source_doc_id", "unknown")
            quote_obj = {
                "text": text,
                "speaker": "",  # No speaker in verse_discovery
                "source": source_type,
                "date": "",
                "ref": "",
                "type": "cross_source",
                "attr": normalize_source_citation(source_type, doc_id),
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
        # Load chapter text for verse-leak detection
        chapter_verses = load_chapter_verses(book, chapter)

        # Merge verse footnotes
        merged = {}
        for verse_num, entries in sorted(verses.items()):
            verse_text = chapter_verses.get(verse_num, "")
            footnote = merge_verse_footnotes(verse_num, entries, verse_text)
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
