#!/usr/bin/env python3
"""Lightweight lint: corpus HTML files from source_toc.json should use p.source-para."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "library"
TOC = LIB / "source_toc.json"


def walk_items(node, out: list[str]) -> None:
    if isinstance(node, dict):
        h = node.get("href")
        if isinstance(h, str) and h.endswith(".html"):
            out.append(h)
        for v in node.values():
            walk_items(v, out)
    elif isinstance(node, list):
        for x in node:
            walk_items(x, out)


def main() -> None:
    if not TOC.is_file():
        print("SKIP: library/source_toc.json missing", file=sys.stderr)
        return
    tree = json.loads(TOC.read_text(encoding="utf-8"))
    hrefs: list[str] = []
    walk_items(tree, hrefs)
    hrefs = sorted(set(hrefs))

    bad: list[str] = []
    for href in hrefs:
        p = LIB / href
        if not p.is_file():
            bad.append(f"{href} (missing file)")
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        n = len(re.findall(r'class="[^"]*source-para', txt))
        if n < 1:
            bad.append(f"{href} (0 source-para)")

    if bad:
        print("Issues:", file=sys.stderr)
        for b in bad[:50]:
            print(f"  {b}", file=sys.stderr)
        if len(bad) > 50:
            print(f"  … {len(bad) - 50} more", file=sys.stderr)
    print(f"lint_source_paras: {len(hrefs)} toc files, {len(bad)} flagged")


if __name__ == "__main__":
    main()
