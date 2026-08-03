#!/usr/bin/env python3
"""Rebuild Come Follow Me week refs from week titles.

The prior generator kept only the first chapter of each range, so week 31
("Ezra 1; 3-7; Nehemiah 2; 4-6; 8") produced just Ezra 1 and Nehemiah 2, and
whole-book weeks (Esther, Malachi) produced nothing at all. Chapter chips and
week-order navigation read these refs, so every chapter in the title has to
land here.

Title grammar, all of which appears in the 2026 manual:
    "Genesis 1-2; Moses 2-3"          book + range per segment
    "Exodus 19-20; 24; 31-34"         bare segment continues the last book
    "Ruth; 1 Samuel 1-7"              bookless segment = whole book
    "Psalms 102-3; 116-19"            abbreviated range end (103, 119)
    "Easter"                          no scripture; refs stay empty

Usage: python3 scripts/regen_cfm_refs.py [--check]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFM = ROOT / "library" / "cfm_2026.json"
TOC = ROOT / "library" / "toc.json"

DASH = re.compile(r"[–—-]")


def load_books():
    """Map book label -> chapter count, from the library's own table of contents."""
    counts = {}
    current = None
    for item in json.loads(TOC.read_text()):
        if item.get("type") == "book":
            current = item["label"]
            counts[current] = 0
        elif item.get("type") == "chapter" and current:
            counts[current] += 1
    return counts


def expand_end(start, end):
    """'102-3' means 102-103; '146-50' means 146-150."""
    while end < start:
        prefix = str(start)[: len(str(start)) - len(str(end))]
        if not prefix:
            return start
        end = int(prefix + str(end))
    return end


def parse_chapters(spec):
    """'19-20' -> [(19, 20)];  '1, 4, 16' -> [(1,1), (4,4), (16,16)]."""
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        bits = [b.strip() for b in DASH.split(part) if b.strip()]
        if not all(b.isdigit() for b in bits):
            return None
        if len(bits) == 1:
            out.append((int(bits[0]), int(bits[0])))
        elif len(bits) == 2:
            start = int(bits[0])
            out.append((start, expand_end(start, int(bits[1]))))
        else:
            return None
    return out or None


def parse_title(title, books):
    """Return refs for a week title, or [] when the week has no scripture block."""
    refs = []
    current_book = None
    for segment in title.split(";"):
        segment = segment.strip()
        if not segment:
            continue

        # Bare chapters continue the book named in an earlier segment.
        chapters = parse_chapters(segment)
        if chapters and current_book:
            for start, end in chapters:
                refs.append((current_book, start, end))
            continue

        # Longest book name wins so "1 Samuel" beats a stray "Samuel".
        match = None
        for name in sorted(books, key=len, reverse=True):
            if segment == name or segment.startswith(name + " "):
                match = name
                break
        if not match:
            continue  # topical week ("Easter", "Introduction to the Old Testament")

        current_book = match
        rest = segment[len(match):].strip()
        if not rest:
            refs.append((match, 1, books[match]))  # whole book
            continue
        chapters = parse_chapters(rest)
        if not chapters:
            continue
        for start, end in chapters:
            refs.append((match, start, end))

    # Clamp to chapters that actually exist so chips never link to a 404.
    clean = []
    for book, start, end in refs:
        total = books[book]
        start, end = max(1, start), min(end, total)
        if start <= end:
            clean.append({"book": book, "chapter_start": start, "chapter_end": end})
    return clean


def main():
    check_only = "--check" in sys.argv
    books = load_books()
    weeks = json.loads(CFM.read_text())

    changed = 0
    computed = []
    for week in weeks:
        new_refs = parse_title(week["title"], books)
        computed.append(new_refs)
        if new_refs != week["refs"]:
            changed += 1
            if not check_only:
                week["refs"] = new_refs

    total_chapters = sum(
        r["chapter_end"] - r["chapter_start"] + 1 for refs in computed for r in refs
    )
    empty = [w["title"] for w, refs in zip(weeks, computed) if not refs]
    print(f"weeks changed: {changed}/{len(weeks)}")
    print(f"chapters covered: {total_chapters}")
    print(f"weeks with no scripture block: {len(empty)} -> {empty}")

    if check_only:
        return 1 if changed else 0
    CFM.write_text(json.dumps(weeks, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {CFM}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
