#!/usr/bin/env python3
"""Build per-chapter translation shards for the reader's Translations tab.

Phase 1 of docs/TRANSLATIONS.md: public-domain translations only. ESV and NIV
are commercially licensed and cannot ship here, so the reader compares KJV
(already the base text) against the World English Bible and the American
Standard Version.

Output is one file per chapter, matching the ids the reader already uses:

    library/translations/<chapter_id>.json
    { "1": {"web": "...", "asv": "..."}, "2": {...} }

Per-chapter files mean the reader fetches a few KB for the chapter in front of
the user instead of a whole-Bible blob, and a CDN can cache each one forever.

Usage:
    python3 scripts/fetch_translations.py            # fetch + write
    python3 scripts/fetch_translations.py --verify   # report coverage only
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOC = ROOT / "library" / "toc.json"
OUT = ROOT / "library" / "translations"
CACHE = ROOT / ".translation-cache"

TRANSLATIONS = ["web", "asv"]
SOURCE = "https://api.getbible.net/v2/{translation}/{book_nr}.json"
BIBLE_VOLUMES = ("Old Testament", "New Testament")


def library_bible_books():
    """Bible books in canonical order: label -> (chapter_id_prefix, chapter_count).

    The source numbers books 1..66 in this same canonical order, so position in
    this list is the source's book number.
    """
    items = json.loads(TOC.read_text())
    volume = book = None
    books = {}
    order = []
    for item in items:
        kind = item.get("type")
        if kind == "volume":
            volume = item["label"]
        elif kind == "book":
            book = item["label"]
            if volume in BIBLE_VOLUMES:
                books[book] = {"prefix": None, "chapters": 0}
                order.append(book)
        elif kind == "chapter" and book in books:
            books[book]["chapters"] += 1
            if books[book]["prefix"] is None:
                books[book]["prefix"] = item["id"].rsplit("_", 1)[0]
    return order, books


def fetch(translation, book_nr):
    """One file per book per translation, cached on disk so re-runs are free."""
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / f"{translation}-{book_nr}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    url = SOURCE.format(translation=translation, book_nr=book_nr)
    # The API answers 403 to Python's default user-agent.
    request = urllib.request.Request(url, headers={"User-Agent": "wescripture-build/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            cached.write_text(json.dumps(payload))
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == 2:
                print(f"  ! {translation} book {book_nr} failed: {exc}")
                return None
            time.sleep(2 * (attempt + 1))
    return None


def main():
    verify_only = "--verify" in sys.argv
    order, books = library_bible_books()

    # chapter_id -> verse -> {translation: text}
    shards = {}
    for index, label in enumerate(order, start=1):
        prefix = books[label]["prefix"]
        for translation in TRANSLATIONS:
            payload = fetch(translation, index)
            if not payload:
                continue
            if payload.get("name") and payload["name"].split()[-1] != label.split()[-1]:
                print(f"  ? book {index}: source says {payload['name']!r}, library says {label!r}")
            for chapter in payload.get("chapters", []):
                chapter_id = f"{prefix}_{chapter['chapter']}"
                verses = shards.setdefault(chapter_id, {})
                for verse in chapter.get("verses", []):
                    text = " ".join((verse.get("text") or "").split())
                    if text:
                        verses.setdefault(str(verse["verse"]), {})[translation] = text

    total_verses = sum(len(v) for v in shards.values())
    both = sum(1 for ch in shards.values() for v in ch.values() if len(v) == len(TRANSLATIONS))
    print(f"chapters: {len(shards)}")
    print(f"verses: {total_verses} ({both} with all {len(TRANSLATIONS)} translations)")

    if verify_only:
        return 0

    OUT.mkdir(exist_ok=True)
    for chapter_id, verses in shards.items():
        ordered = {k: verses[k] for k in sorted(verses, key=int)}
        (OUT / f"{chapter_id}.json").write_text(
            json.dumps(ordered, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
    print(f"wrote {len(shards)} files to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
