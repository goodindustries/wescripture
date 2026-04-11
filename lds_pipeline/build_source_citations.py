#!/usr/bin/env python3
"""
Extract scripture-style references from source HTML paragraphs.
Output: library/source_citations.json
  { "doc_id": { "para_1based": [ { "chapterId", "v", "ch", "raw" }, ... ] } }

Run from repo root: python3 lds_pipeline/build_source_citations.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIBRARY = REPO / "library"
BOOKS = LIBRARY / "entities" / "books.json"
SOURCE_TOC = LIBRARY / "source_toc.json"
OUT = LIBRARY / "source_citations.json"

# One scan per paragraph: book phrase + chapter:verse
REF_RE = re.compile(
    r"\b([\w][\w\s,\.'\u2014\-]{1,62}?)\s+(\d+)\s*:\s*(\d+)\b",
    re.UNICODE,
)


def load_books() -> dict[str, str]:
    data = json.loads(BOOKS.read_text(encoding="utf-8"))
    m: dict[str, str] = {}
    for b in data:
        slug = b.get("slug") or ""
        if not slug:
            continue
        for key in (b.get("name"), b.get("abbreviation")):
            if key:
                k = re.sub(r"\s+", " ", key.lower().strip())
                m[k] = slug
    return m


def strip_tags(html: str) -> str:
    t = re.sub(r"<[^>]+>", " ", html)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def find_refs(text: str, name_to_slug: dict[str, str]) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple] = set()

    def add(slug: str, ch: int, v: int, raw: str) -> None:
        key = (slug, ch, v)
        if key in seen:
            return
        seen.add(key)
        out.append({"chapterId": f"{slug}_{ch}", "v": v, "ch": ch, "raw": raw})

    # D&C variants first (book group may not be in name map the same way)
    for m in re.finditer(
        r"\b(?:D\s*&\s*C|D\.?\s*C\.?|Doctrine\s+and\s+Covenants)\s+(\d+)\s*:\s*(\d+)",
        text,
        re.I,
    ):
        add("doctrine_and_covenants", int(m.group(1)), int(m.group(2)), m.group(0).strip())

    for m in REF_RE.finditer(text):
        book_part = re.sub(r"\s+", " ", m.group(1).strip())
        ch = int(m.group(2))
        v = int(m.group(3))
        raw = m.group(0).strip()
        key = book_part.lower().strip(" .,'\"")
        key = re.sub(r"^[\d\s]+", "", key).strip() or key
        slug = name_to_slug.get(key)
        if not slug:
            # "1 Nephi" etc. — key may include leading number
            slug = name_to_slug.get(book_part.lower().strip())
        if slug and slug != "doctrine_and_covenants":
            add(slug, ch, v, raw)

    return out


def extract_doc(doc_id: str, href: str, name_to_slug: dict[str, str]) -> dict[str, list] | None:
    path = LIBRARY / href
    if not path.exists():
        return None
    html = path.read_text(encoding="utf-8", errors="replace")
    if len(html) > 1_200_000:
        html = html[:1_200_000]
    paras = re.findall(
        r'<p[^>]*class="[^"]*source-para[^"]*"[^>]*>(.*?)</p>',
        html,
        re.S | re.I,
    )
    by_para: dict[str, list] = {}
    for i, raw in enumerate(paras, start=1):
        text = strip_tags(raw)
        if len(text) < 14:
            continue
        refs = find_refs(text, name_to_slug)
        if refs:
            by_para[str(i)] = refs
    return by_para or None


def main() -> None:
    name_to_slug = load_books()
    toc = json.loads(SOURCE_TOC.read_text(encoding="utf-8"))
    index: dict = {}
    for coll in toc:
        for it in coll.get("items") or []:
            if it.get("type") == "group":
                items = it.get("items") or []
            else:
                items = [it]
            for item in items:
                did = item.get("id")
                href = item.get("href")
                if not did or not href:
                    continue
                block = extract_doc(did, href, name_to_slug)
                if block:
                    index[did] = block

    OUT.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(index):,} documents with citations → {OUT}")


if __name__ == "__main__":
    main()
