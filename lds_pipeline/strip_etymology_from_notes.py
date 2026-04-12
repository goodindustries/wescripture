#!/usr/bin/env python3
"""Remove legacy .etymology-block markup from library/chapters/*_notes.html."""

from __future__ import annotations

import argparse
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
NOTES_GLOB = REPO / "library" / "chapters" / "*_notes.html"


def strip_file(path: Path, dry_run: bool) -> int:
    raw = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    blocks = soup.select(".etymology-block")
    n = len(blocks)
    if not n:
        return 0
    for b in blocks:
        b.decompose()
    if not dry_run:
        path.write_text(str(soup), encoding="utf-8")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Count only; do not write files")
    args = ap.parse_args()

    total_blocks = 0
    files_touched = 0
    for path in sorted(NOTES_GLOB.parent.glob(NOTES_GLOB.name)):
        removed = strip_file(path, args.dry_run)
        if removed:
            files_touched += 1
            total_blocks += removed
            if args.dry_run:
                print(f"{path.name}: would remove {removed} .etymology-block(s)")

    suffix = " (dry-run)" if args.dry_run else ""
    print(f"strip_etymology_from_notes: {files_touched} files, {total_blocks} blocks{suffix}")


if __name__ == "__main__":
    main()
