#!/usr/bin/env python3
"""
Future: normalize whitespace in <p class="source-para"> across library/sources/**.
Run only after backing up. Not executed by default.

  python3 lds_pipeline/normalize_source_paragraphs.py --dry-run
"""

import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCES = REPO / "library" / "sources"


def normalize_para_inner(html: str) -> str:
    t = re.sub(r"\s+", " ", html)
    return t.strip()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    n = 0
    for f in sorted(SOURCES.rglob("*.html")):
        raw = f.read_text(encoding="utf-8", errors="replace")
        if "source-para" not in raw:
            continue
        n += 1
    print(f"Found {n:,} HTML files with source-para under {SOURCES}")
    print("No files modified (stub). Use --dry-run only until a normalization policy is set.")


if __name__ == "__main__":
    main()
