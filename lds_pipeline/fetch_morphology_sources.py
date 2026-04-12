#!/usr/bin/env python3
"""
Download MorphGNT (NT) and OSHB WLC XML (OT) into lds_pipeline/cache/morphology/.

Run from repo root:
  python3 lds_pipeline/fetch_morphology_sources.py
  python3 lds_pipeline/fetch_morphology_sources.py --books Gen Exod
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "lds_pipeline" / "cache" / "morphology"
MORPHGNT_BASE = "https://raw.githubusercontent.com/morphgnt/sblgnt/master"
OSHB_BASE = "https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc"

# morphgnt/sblgnt filenames use 61-Mt … 87-Re
NT_FILES: list[tuple[str, str]] = [
    ("61-Mt-morphgnt.txt", "Mt"),
    ("62-Mk-morphgnt.txt", "Mk"),
    ("63-Lk-morphgnt.txt", "Lk"),
    ("64-Jn-morphgnt.txt", "Jn"),
    ("65-Ac-morphgnt.txt", "Ac"),
    ("66-Ro-morphgnt.txt", "Ro"),
    ("67-1Co-morphgnt.txt", "1Co"),
    ("68-2Co-morphgnt.txt", "2Co"),
    ("69-Ga-morphgnt.txt", "Ga"),
    ("70-Eph-morphgnt.txt", "Eph"),
    ("71-Php-morphgnt.txt", "Php"),
    ("72-Col-morphgnt.txt", "Col"),
    ("73-1Th-morphgnt.txt", "1Th"),
    ("74-2Th-morphgnt.txt", "2Th"),
    ("75-1Ti-morphgnt.txt", "1Ti"),
    ("76-2Ti-morphgnt.txt", "2Ti"),
    ("77-Tit-morphgnt.txt", "Tit"),
    ("78-Phm-morphgnt.txt", "Phm"),
    ("79-Heb-morphgnt.txt", "Heb"),
    ("80-Jas-morphgnt.txt", "Jas"),
    ("81-1Pe-morphgnt.txt", "1Pe"),
    ("82-2Pe-morphgnt.txt", "2Pe"),
    ("83-1Jn-morphgnt.txt", "1Jn"),
    ("84-2Jn-morphgnt.txt", "2Jn"),
    ("85-3Jn-morphgnt.txt", "3Jn"),
    ("86-Jud-morphgnt.txt", "Jud"),
    ("87-Re-morphgnt.txt", "Re"),
]

OT_BOOK_FILES = [
    "Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth", "1Sam", "2Sam",
    "1Kgs", "2Kgs", "1Chr", "2Chr", "Ezra", "Neh", "Esth", "Job", "Ps", "Prov",
    "Eccl", "Song", "Isa", "Jer", "Lam", "Ezek", "Dan", "Hos", "Joel", "Amos",
    "Obad", "Jonah", "Mic", "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal",
]


def _fetch(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100:
        return False
    print(f"  fetch {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "WeScriptureMorphologyFetcher/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nt-only", action="store_true")
    ap.add_argument("--ot-only", action="store_true")
    ap.add_argument("--books", nargs="*", help="OT OSIS book codes, e.g. Gen Exod")
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    n = 0
    if not args.ot_only:
        for fn, _abbr in NT_FILES:
            url = f"{MORPHGNT_BASE}/{fn}"
            if _fetch(url, CACHE / fn):
                n += 1
    if not args.nt_only:
        books = args.books if args.books else OT_BOOK_FILES
        for osis in books:
            fn = f"{osis}.xml"
            url = f"{OSHB_BASE}/{fn}"
            if _fetch(url, CACHE / fn):
                n += 1
    print(f"fetch_morphology_sources: wrote {n} new file(s) under {CACHE}", flush=True)


if __name__ == "__main__":
    main()
