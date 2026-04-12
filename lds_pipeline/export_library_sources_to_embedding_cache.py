#!/usr/bin/env python3
"""
Export canonical paragraphs from shipped library HTML (p.source-para) into
lds_pipeline/cache flat *.txt files so correlate_embeddings.load_all_sources()
uses the same paragraph boundaries as the reader / source_toc counts.

Run from repo root:
  python3 lds_pipeline/export_library_sources_to_embedding_cache.py --dry-run
  python3 lds_pipeline/export_library_sources_to_embedding_cache.py --apply

Requires: beautifulsoup4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
LIBRARY = REPO / "library"
CACHE = REPO / "lds_pipeline" / "cache"
SOURCE_TOC = LIBRARY / "source_toc.json"

# source_toc collection id -> cache subdirectory (flat *.txt per href stem)
TOC_TO_CACHE_DIR: dict[str, str] = {
    "general_conference": "general_conference",
    "journal_of_discourses": "jd",
    "history_of_church": "hoc",
    "joseph_smith_papers": "joseph_smith_papers",
    "gutenberg_lds": "gutenberg_lds",
    "church_fathers": "church_fathers",
    "millennial_star": "millennial_star",
    "times_and_seasons": "times_and_seasons",
    "pioneer_journals": "pioneer_journals",
}

ANCIENT_TEXTS_CACHE_DIRS = (
    "ancient_myths",
    "pseudepigrapha",
    "apocrypha",
    "nag_hammadi",
    "dead_sea_scrolls",
)


def flatten_toc_leaves() -> list[dict]:
    data = json.loads(SOURCE_TOC.read_text(encoding="utf-8"))
    out: list[dict] = []
    for coll in data:
        cid = coll.get("id", "")

        def walk(items: list, collection_id: str) -> None:
            for it in items or []:
                if it.get("type") == "group":
                    walk(it.get("items") or [], collection_id)
                elif it.get("href"):
                    out.append({
                        "collection_id": collection_id,
                        "doc_id": it.get("id", ""),
                        "href": it.get("href", ""),
                    })

        walk(coll.get("items") or [], cid)
    return out


def paragraphs_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    paras: list[str] = []
    for p in soup.select("p.source-para"):
        text = p.get_text(" ", strip=True)
        if text:
            paras.append(text)
    return paras


def ancient_dest_path(stem: str) -> Path:
    for sub in ANCIENT_TEXTS_CACHE_DIRS:
        p = CACHE / sub / f"{stem}.txt"
        if p.is_file():
            return p
    return CACHE / "ancient_myths" / f"{stem}.txt"


def cache_txt_path(row: dict) -> Path | None:
    cid = row["collection_id"]
    href = row.get("href") or ""
    if not href.endswith(".html"):
        return None
    stem = Path(href).stem
    if cid == "ancient_texts":
        return ancient_dest_path(stem)
    sub = TOC_TO_CACHE_DIR.get(cid)
    if not sub:
        return None
    return CACHE / sub / f"{stem}.txt"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export library HTML paragraphs to embedding cache .txt")
    parser.add_argument("--apply", action="store_true", help="Write files (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Print counts only (default)")
    args = parser.parse_args()
    dry = not args.apply

    if not SOURCE_TOC.exists():
        print(f"Missing {SOURCE_TOC}", file=sys.stderr)
        return 1

    leaves = flatten_toc_leaves()
    would_write = 0
    skipped = 0
    missing_html = 0
    empty_paras = 0

    for row in leaves:
        dest = cache_txt_path(row)
        if dest is None:
            skipped += 1
            continue
        html_path = LIBRARY / row["href"]
        if not html_path.is_file():
            missing_html += 1
            continue
        html_text = html_path.read_text(encoding="utf-8", errors="replace")
        paras = paragraphs_from_html(html_text)
        if not paras:
            empty_paras += 1
            continue
        body = "\n\n".join(paras)
        if len(body) < 40:
            empty_paras += 1
            continue
        would_write += 1
        if not dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")

    mode = "dry-run" if dry else "apply"
    print(
        f"[{mode}] toc_leaves={len(leaves)} write={would_write} "
        f"skipped_no_cache_mapping={skipped} missing_html={missing_html} empty_short={empty_paras}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
