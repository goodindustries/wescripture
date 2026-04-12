#!/usr/bin/env python3
"""
Inject <h3 class="chapter-heading"> into library/chapters/*.html from library/chapter_headings.json.

Skips files that already contain chapter-heading or _notes / title_page.

Run from repo root:
  python3 lds_pipeline/apply_chapter_headings_to_html.py
"""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
LIB = _REPO / "library" / "chapters"
HEADINGS_PATH = _REPO / "library" / "chapter_headings.json"


def main() -> None:
    if not HEADINGS_PATH.exists():
        print(f"Missing {HEADINGS_PATH} — run fetch_chapter_headings.py first")
        return
    headings: dict[str, str] = json.loads(HEADINGS_PATH.read_text(encoding="utf-8"))
    updated = 0
    for path in sorted(LIB.glob("*.html")):
        name = path.name
        if "_notes" in name or name == "title_page.html":
            continue
        text = path.read_text(encoding="utf-8")
        if "chapter-heading" in text:
            continue
        m = re.search(r'<meta[^>]+name="chapter-id"[^>]+content="([^"]+)"', text)
        if not m:
            continue
        ch_id = m.group(1)
        summary = headings.get(ch_id)
        if not summary:
            continue
        h3 = f'<h3 class="chapter-heading">{escape(summary)}</h3>\n'
        if '<div class="scripture">' in text:
            new_text = text.replace("<div class=\"scripture\">", "<div class=\"scripture\">\n" + h3, 1)
        else:
            continue
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            updated += 1
    print(f"  updated {updated} chapter HTML files with headings")


if __name__ == "__main__":
    main()
