#!/usr/bin/env python3
"""Drop Donaldson "notes" that are really adjacent scripture text.

The extractor sometimes swept the next verse's scripture into the previous
verse's note list, so 1 Chronicles 15:25 carried "26 And it came to pass..."
— the whole of verse 26 — as commentary. In the reader that shows up as a
commentary card repeating scripture the user just read.

A note is removed only when it is proven to be scripture: it opens with a
verse number, and after normalization its body matches that verse's actual
text in library/chapters/<chapter>.html. Pattern alone is never enough, since
real commentary also quotes verses.

Usage: python3 scripts/strip_donaldson_verse_bleed.py [--check]
"""
import json
import re
import sys
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DONALDSON = ROOT / "library" / "donaldson"
CHAPTERS = ROOT / "library" / "chapters"

VERSE_DIV = re.compile(r'<div class="verse" id="v(\d+)">(.*?)</div>', re.S)
TAG = re.compile(r"<[^>]+>")
LEAD_VERSE_NUM = re.compile(r"^\s*(\d+)\s+(?=[A-Za-z(\[])")
# Match on letters only: punctuation, brackets and spacing differ between the
# rendered chapter and the extracted note.
NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize(text):
    return NON_ALNUM.sub("", unescape(TAG.sub(" ", text)).lower())


def chapter_verses(chapter_id):
    path = CHAPTERS / f"{chapter_id}.html"
    if not path.exists():
        return {}
    html = path.read_text(errors="ignore")
    verses = {}
    for num, body in VERSE_DIV.findall(html):
        body = re.sub(r'<span class="verse-num">.*?</span>', " ", body, flags=re.S)
        verses[int(num)] = normalize(body)
    return verses


def note_text(note):
    return note if isinstance(note, str) else (note.get("text") or "")


def is_verse_bleed(note, verses):
    text = note_text(note)
    match = LEAD_VERSE_NUM.match(text)
    if not match:
        return False
    verse_num = int(match.group(1))
    target = verses.get(verse_num)
    if not target:
        return False
    body = normalize(text[match.end():])
    if len(body) < 30:
        return False
    # The note must BE the verse, not merely quote it inside longer commentary.
    return body == target or (body in target and len(body) / len(target) > 0.9)


def main():
    check_only = "--check" in sys.argv
    removed = []
    files_changed = 0

    for path in sorted(DONALDSON.glob("*.json")):
        data = json.loads(path.read_text())
        verses = chapter_verses(path.stem)
        if not verses:
            continue
        dirty = False
        for verse_key, entry in data.items():
            notes = entry.get("notes")
            if not notes:
                continue
            keep = [n for n in notes if not is_verse_bleed(n, verses)]
            if len(keep) != len(notes):
                dirty = True
                for n in notes:
                    if is_verse_bleed(n, verses):
                        removed.append(f"{path.stem}:{verse_key} -> {note_text(n)[:70]}")
                if keep:
                    entry["notes"] = keep
                else:
                    entry.pop("notes")
        if dirty:
            # An entry whose only content was bled scripture has nothing to say;
            # leaving {} behind would claim commentary this verse never had.
            for verse_key in [k for k, v in data.items() if not v]:
                del data[verse_key]
            files_changed += 1
            if not check_only:
                path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")

    print(f"files with bleed: {files_changed}")
    print(f"notes removed: {len(removed)}")
    for line in removed[:15]:
        print("  " + line)
    if len(removed) > 15:
        print(f"  ... {len(removed) - 15} more")
    if check_only:
        return 1 if removed else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
