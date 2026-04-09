#!/usr/bin/env python3
"""
Normalize Donaldson commentary JSON files.

Operations per file:
  - Remove preamble-only notes (chapter/section range headers, bare translation quotes)
  - Normalize whitespace in all text fields (collapse runs, strip)
  - Convert notes[] from plain strings to {"p": N, "text": "..."} objects
  - Clean quotes[].text whitespace

Semantic paragraph IDs become: donaldson:{chapter_id}:{verse}:p{n}
"""

import json
import os
import re
import sys

DONA_DIR = os.path.join(os.path.dirname(__file__), '..', 'library', 'donaldson')

# Patterns that identify a note as a non-content preamble to discard
PREAMBLE_PATTERNS = [
    re.compile(r'^\s*\d[\d:,\-]+\s*[-–.]\s+[A-Z]{3}'),           # "11:1-34. CENSURE..."
    re.compile(r'^\s*(NASB|KJV|NIV|RSV|ESV|ASV|NLT|NKJV|NAS)\s*:'),  # "NASB: What! ..."
    re.compile(r'^\s*[A-Z]{4,}(?:\s+[A-Z]{2,})*\s*:?\s*$'),      # ALL CAPS HEADER only
]


def is_preamble(text: str) -> bool:
    for pat in PREAMBLE_PATTERNS:
        if pat.match(text):
            return True
    return False


def clean_text(text: str) -> str:
    """Normalize whitespace: collapse runs of spaces/tabs, strip ends."""
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    return text


def normalize_file(path: str) -> tuple[int, int]:
    """Returns (notes_removed, files_changed)."""
    with open(path) as f:
        data = json.load(f)

    changed = False
    total_removed = 0

    for vk, vdata in data.items():
        if not isinstance(vdata, dict):
            continue

        # --- notes ---
        raw_notes = vdata.get('notes', [])
        new_notes = []
        para_num = 0
        for note in raw_notes:
            if not isinstance(note, str):
                # Already an object — re-clean text field
                if isinstance(note, dict) and 'text' in note:
                    cleaned = clean_text(note['text'])
                    if not cleaned or is_preamble(cleaned):
                        total_removed += 1
                        changed = True
                        continue
                    if cleaned != note['text']:
                        note = dict(note, text=cleaned)
                        changed = True
                    para_num += 1
                    new_notes.append(dict(note, p=para_num))
                continue

            cleaned = clean_text(note)
            if not cleaned or is_preamble(cleaned):
                total_removed += 1
                changed = True
                continue
            para_num += 1
            new_notes.append({'p': para_num, 'text': cleaned})
            changed = True  # structure changed (string → object)

        if new_notes != raw_notes:
            vdata['notes'] = new_notes

        # --- quotes: clean text field only ---
        for q in vdata.get('quotes', []):
            if isinstance(q, dict) and 'text' in q:
                cleaned = clean_text(q['text'])
                if cleaned != q['text']:
                    q['text'] = cleaned
                    changed = True

        # --- words: clean plain/meaning fields ---
        for w in vdata.get('words', []):
            if isinstance(w, dict):
                for field in ('plain', 'meaning'):
                    if field in w and isinstance(w[field], str):
                        cleaned = clean_text(w[field])
                        if cleaned != w[field]:
                            w[field] = cleaned
                            changed = True

    if changed:
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    return total_removed, 1 if changed else 0


def main():
    dona_dir = os.path.realpath(DONA_DIR)
    files = sorted(f for f in os.listdir(dona_dir) if f.endswith('.json'))
    total_removed = 0
    total_changed = 0
    for fn in files:
        removed, changed = normalize_file(os.path.join(dona_dir, fn))
        total_removed += removed
        total_changed += changed

    print(f'Processed {len(files)} files.')
    print(f'Files modified: {total_changed}')
    print(f'Preamble notes removed: {total_removed}')
    print(f'Notes now stored as {{p, text}} objects.')


if __name__ == '__main__':
    main()
