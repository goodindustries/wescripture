#!/usr/bin/env python3
"""
Download LDS chapter study summaries from Church study API HTML (<p class="study-summary">).

Writes library/chapter_headings.json as { "genesis_1": "God creates...", ... }.

Run from repo root:
  python3 lds_pipeline/fetch_chapter_headings.py
  python3 lds_pipeline/fetch_chapter_headings.py --max-chapters 80
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
OUT_PATH = _REPO / "library" / "chapter_headings.json"

BASE_API = "https://www.churchofjesuschrist.org/study/api/v3/language-pages/type/content"

WORKS = [
    ("Old Testament", "ot", "/scriptures/ot"),
    ("New Testament", "nt", "/scriptures/nt"),
    ("Book of Mormon", "bofm", "/scriptures/bofm"),
    ("Doctrine and Covenants", "dc-testament", "/scriptures/dc-testament"),
    ("Pearl of Great Price", "pgp", "/scriptures/pgp"),
]

SLUG_TO_BOOK = {
    "gen": "Genesis", "ex": "Exodus", "lev": "Leviticus", "num": "Numbers",
    "deut": "Deuteronomy", "josh": "Joshua", "judg": "Judges", "ruth": "Ruth",
    "1-sam": "1 Samuel", "2-sam": "2 Samuel", "1-kgs": "1 Kings", "2-kgs": "2 Kings",
    "1-chr": "1 Chronicles", "2-chr": "2 Chronicles", "ezra": "Ezra", "neh": "Nehemiah",
    "esth": "Esther", "job": "Job", "ps": "Psalms", "prov": "Proverbs",
    "eccl": "Ecclesiastes", "song": "Song of Solomon", "isa": "Isaiah",
    "jer": "Jeremiah", "lam": "Lamentations", "ezek": "Ezekiel", "dan": "Daniel",
    "hosea": "Hosea", "joel": "Joel", "amos": "Amos", "obad": "Obadiah",
    "jonah": "Jonah", "micah": "Micah", "nahum": "Nahum", "hab": "Habakkuk",
    "zeph": "Zephaniah", "hag": "Haggai", "zech": "Zechariah", "mal": "Malachi",
    "matt": "Matthew", "mark": "Mark", "luke": "Luke", "john": "John",
    "acts": "Acts", "rom": "Romans", "1-cor": "1 Corinthians", "2-cor": "2 Corinthians",
    "gal": "Galatians", "eph": "Ephesians", "philip": "Philippians", "col": "Colossians",
    "1-thes": "1 Thessalonians", "2-thes": "2 Thessalonians",
    "1-tim": "1 Timothy", "2-tim": "2 Timothy", "titus": "Titus",
    "philem": "Philemon", "heb": "Hebrews", "james": "James",
    "1-pet": "1 Peter", "2-pet": "2 Peter", "1-jn": "1 John",
    "2-jn": "2 John", "3-jn": "3 John", "jude": "Jude", "rev": "Revelation",
    "1-ne": "1 Nephi", "2-ne": "2 Nephi", "jacob": "Jacob", "enos": "Enos",
    "jarom": "Jarom", "omni": "Omni", "w-of-m": "Words of Mormon", "mosiah": "Mosiah",
    "alma": "Alma", "hel": "Helaman", "3-ne": "3 Nephi", "4-ne": "4 Nephi",
    "morm": "Mormon", "ether": "Ether", "moro": "Moroni",
    "dc": "Doctrine and Covenants",
    "moses": "Moses", "abr": "Abraham", "js-m": "Joseph Smith—Matthew",
    "js-h": "Joseph Smith—History", "a-of-f": "Articles of Faith",
}


def _slug(s: str) -> str:
    return re.sub(r"[^\w]", "_", s).lower()


def fetch(uri: str, retries: int = 3) -> bytes:
    url = f"{BASE_API}?lang=eng&uri={urllib.parse.quote(uri, safe='/')}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 WeScripture-headings/1.0"})
            return urllib.request.urlopen(req, timeout=40).read()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def get_chapter_uris(work_uri: str) -> list[str]:
    data = json.loads(fetch(work_uri))
    body = data.get("content", {}).get("body", "")
    links = re.findall(r'href="(/study/scriptures/[^"?]+)(?:\?[^"]*)?"', body)
    return [l for l in links if re.search(r"/\d+$", l)]


def extract_study_summary(html_body: str) -> str:
    m = re.search(
        r'<p class="study-summary"[^>]*>(.*?)</p>',
        html_body,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return ""
    inner = m.group(1)
    inner = re.sub(r"<[^>]+>", " ", inner)
    inner = html_module.unescape(inner)
    return re.sub(r"\s+", " ", inner).strip()


def church_uri_to_chapter_id(ch_uri: str) -> str | None:
    parts = ch_uri.rstrip("/").split("/")
    if len(parts) < 2:
        return None
    ch_num = int(parts[-1])
    book_slug = parts[-2]
    book = SLUG_TO_BOOK.get(book_slug)
    if not book:
        book = book_slug.replace("-", " ").title()
    return _slug(f"{book}_{ch_num}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-chapters", type=int, default=0, help="Stop after N fetches (0 = all)")
    args = parser.parse_args()

    headings: dict[str, str] = {}
    if OUT_PATH.exists():
        try:
            headings = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            headings = {}

    fetched = 0
    for _vol, _key, work_uri in WORKS:
        print(f"  TOC {work_uri} …", flush=True)
        chapter_uris = get_chapter_uris(work_uri)
        print(f"    {len(chapter_uris)} chapter links", flush=True)
        for ch_uri in chapter_uris:
            if args.max_chapters and fetched >= args.max_chapters:
                OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
                OUT_PATH.write_text(json.dumps(headings, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"  (--max-chapters) wrote {len(headings)} entries → {OUT_PATH}")
                return
            ch_id = church_uri_to_chapter_id(ch_uri)
            if not ch_id:
                continue
            api_uri = ch_uri.replace("/study", "")
            try:
                data = json.loads(fetch(api_uri))
                body = data.get("content", {}).get("body", "")
                summary = extract_study_summary(body)
                if summary:
                    headings[ch_id] = summary
                time.sleep(0.12)
            except Exception as e:
                print(f"    WARN {api_uri}: {e}", flush=True)
            fetched += 1
            if fetched % 250 == 0:
                OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
                OUT_PATH.write_text(json.dumps(headings, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"    …checkpoint {fetched} fetches, {len(headings)} with summaries", flush=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(headings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  wrote {len(headings)} chapter headings → {OUT_PATH}")


if __name__ == "__main__":
    main()
