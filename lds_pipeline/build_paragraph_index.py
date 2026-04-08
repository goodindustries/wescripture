#!/usr/bin/env python3
"""
build_paragraph_index.py
========================
Extract paragraphs from all source HTML documents and build a paragraph index.
This enables source documents to be treated as first-class readable content —
each paragraph is clickable and opens the same study panel as a scripture verse,
showing related verses, topics, and connections.

Outputs:
  library/para_index.json     — { "doc_id:para_idx": { text, author, work, collection } }
  library/para_verse_map.json — { "doc_id:para_idx": ["Book Ch:V", ...] }  (from source_links.json)

Run from repo root:
    python3 lds_pipeline/build_paragraph_index.py
    python3 lds_pipeline/build_paragraph_index.py --collection general_conference
"""

import argparse
import json
import re
from pathlib import Path

REPO       = Path(__file__).resolve().parent.parent
SOURCES    = REPO / "library" / "sources"
OUT_DIR    = REPO / "library"
SOURCE_TOC = REPO / "library" / "source_toc.json"
SOURCE_LNK = REPO / "library" / "source_links.json"

MIN_PARA_LEN = 80    # characters — skip headings and noise
MAX_PARA_LEN = 2000  # trim extremely long paras


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"')


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_PARA_LEN] if len(text) > MAX_PARA_LEN else text


def extract_paragraphs(html: str) -> list[str]:
    """Extract text from <p class="source-para"> elements."""
    paras = []
    for m in re.finditer(r'<p[^>]*class="[^"]*source-para[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE):
        text = clean(strip_tags(m.group(1)))
        if len(text) >= MIN_PARA_LEN:
            paras.append(text)
    # Fallback: all <p> tags if no source-para class found
    if not paras:
        for m in re.finditer(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE):
            text = clean(strip_tags(m.group(1)))
            if len(text) >= MIN_PARA_LEN:
                paras.append(text)
    return paras


def parse_doc_meta(html: str) -> dict:
    """Extract author and title from source HTML header."""
    meta = {}
    title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    if title_m:
        meta["title"] = clean(strip_tags(title_m.group(1)))
    author_m = re.search(r'class="source-author"[^>]*>(.*?)<', html, re.DOTALL | re.IGNORECASE)
    if author_m:
        meta["author"] = clean(strip_tags(author_m.group(1)))
    # GC pattern: "GC 2021/04 — Elder Holland"
    gc_m = re.search(r'GC\s+(\d{4}/\d{2})\s*[—\-]\s*(.+)', meta.get("title", ""))
    if gc_m:
        meta["date"]   = gc_m.group(1)
        meta["author"] = gc_m.group(2).strip()
    return meta


def build_collection_meta(source_toc: list) -> dict:
    """doc_id prefix → collection label."""
    result = {}
    for entry in source_toc:
        result[entry["id"]] = entry.get("label", entry["id"])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", default="", help="Process only this collection")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()

    source_toc  = json.loads(SOURCE_TOC.read_text(encoding="utf-8")) if SOURCE_TOC.exists() else []
    source_links = json.loads(SOURCE_LNK.read_text(encoding="utf-8")) if SOURCE_LNK.exists() else {}
    coll_labels  = build_collection_meta(source_toc)

    para_index    = {}   # "doc_id:para_idx" → {text, author, work, collection}
    para_verse_map = {}  # "doc_id:para_idx" → ["Book Ch:V", ...]

    collections = sorted(SOURCES.iterdir()) if SOURCES.exists() else []
    if args.collection:
        collections = [c for c in collections if c.name == args.collection]

    total_paras = 0

    for coll_dir in collections:
        if not coll_dir.is_dir():
            continue
        coll_id    = coll_dir.name
        coll_label = coll_labels.get(coll_id, coll_id)
        html_files = sorted(coll_dir.glob("*.html"))
        print(f"{coll_id}: {len(html_files)} docs", flush=True)

        for html_path in html_files:
            doc_id  = html_path.stem
            full_id = f"{coll_id}:{doc_id}"
            try:
                html = html_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"  skip {doc_id}: {e}", flush=True)
                continue

            doc_meta = parse_doc_meta(html)
            paras    = extract_paragraphs(html)

            # Lookup verse links for this doc (1-based para index in source_links)
            doc_links = source_links.get(full_id, {})

            for idx, text in enumerate(paras):
                para_key  = f"{full_id}:{idx + 1}"
                verse_refs = [v["ref"] for v in doc_links.get(str(idx + 1), [])]

                para_index[para_key] = {
                    "text":       text,
                    "author":     doc_meta.get("author", ""),
                    "work":       doc_meta.get("title", ""),
                    "date":       doc_meta.get("date", ""),
                    "collection": coll_label,
                    "doc_id":     full_id,
                    "para_idx":   idx + 1,
                }
                if verse_refs:
                    para_verse_map[para_key] = verse_refs

            total_paras += len(paras)

    print(f"\nTotal: {total_paras:,} paragraphs indexed across {len(collections)} collections")
    print(f"Para-verse mappings: {len(para_verse_map):,} linked paragraphs")

    if not args.dry_run:
        # Write per-collection indexes (loadable on demand, manageable sizes)
        para_dir = OUT_DIR / "para"
        para_dir.mkdir(exist_ok=True)
        by_coll: dict[str, dict] = {}
        for key, entry in para_index.items():
            coll = entry.get("doc_id", "").split(":")[0] if ":" in entry.get("doc_id", "") else "unknown"
            by_coll.setdefault(coll, {})[key] = entry
        for coll, entries in by_coll.items():
            out_path = para_dir / f"{coll}.json"
            out_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
            size_kb = out_path.stat().st_size // 1024
            print(f"  Wrote library/para/{coll}.json ({size_kb}KB, {len(entries)} paras)")

        # Small para→verse map (all collections combined, 207KB)
        (OUT_DIR / "para_verse_map.json").write_text(
            json.dumps(para_verse_map, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"Wrote library/para_verse_map.json ({len(para_verse_map)} linked)")
    else:
        print("[dry-run] no files written")


if __name__ == "__main__":
    main()
