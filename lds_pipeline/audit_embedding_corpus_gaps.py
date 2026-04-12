#!/usr/bin/env python3
"""
Compare shipped source_toc documents to passages produced by correlate_embeddings.load_all_sources().

- Layer A: collections with TOC paragraphs > 0 but zero passages for that source key.
- Layer B: flat per-doc shelves (GC, JD, HoC, JSP, …): each TOC leaf's HTML stem must have a matching .txt in cache (ancient_texts tries several subdirs).

Run from repo root after cache sync + verse catalog exist:
  python3 lds_pipeline/audit_embedding_corpus_gaps.py
  python3 lds_pipeline/audit_embedding_corpus_gaps.py --strict   # exit 1 if gaps

Without catalog or cache, exits 0 and writes a skipped summary.
Output: diagnostics/embedding_loader_gaps.json
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LIBRARY = REPO / "library"
SOURCE_TOC = LIBRARY / "source_toc.json"
CACHE = REPO / "lds_pipeline" / "cache"
CATALOG_PRIMARY = CACHE / "verse_catalog.json"
CATALOG_FALLBACK = CACHE / "standard_works" / "verse_catalog.json"
OUT_JSON = REPO / "diagnostics" / "embedding_loader_gaps.json"

# source_toc collection id -> passage["source"] keys in correlate_embeddings.load_all_sources
TOC_TO_PASSAGE_SOURCES: dict[str, list[str]] = {
    "ancient_texts": [
        "ancient_myths",
        "pseudepigrapha",
        "apocrypha",
        "nag_hammadi",
        "dead_sea_scrolls",
    ],
}

# source_toc collection id -> lds_pipeline/cache subdirectory (flat *.txt per doc stem)
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

# For ancient_texts leaves, try these cache dirs for {stem}.txt (first hit counts as present)
ANCIENT_TEXTS_CACHE_DIRS = ("ancient_myths", "pseudepigrapha", "apocrypha", "nag_hammadi", "dead_sea_scrolls")


def passage_count_for_toc_collection(collection_id: str, by_source: Counter) -> int:
    keys = TOC_TO_PASSAGE_SOURCES.get(collection_id, [collection_id])
    return sum(by_source.get(k, 0) for k in keys)


def flatten_toc_leaves() -> list[dict]:
    data = json.loads(SOURCE_TOC.read_text(encoding="utf-8"))
    out = []
    for coll in data:
        cid = coll.get("id", "")

        def walk(items, collection_id: str):
            for it in items or []:
                if it.get("type") == "group":
                    walk(it.get("items") or [], collection_id)
                elif it.get("href"):
                    out.append({
                        "collection_id": collection_id,
                        "doc_id": it.get("id", ""),
                        "href": it.get("href", ""),
                        "paragraphs": int(it.get("paragraphs") or 0),
                    })

        walk(coll.get("items") or [], cid)
    return out


def load_catalog() -> list[dict] | None:
    path = CATALOG_PRIMARY if CATALOG_PRIMARY.exists() else CATALOG_FALLBACK
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def import_load_all_sources():
    mod_path = REPO / "lds_pipeline" / "correlate_embeddings.py"
    spec = importlib.util.spec_from_file_location("correlate_embeddings", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load_all_sources


def _monolithic_periodical_skip(cache_dir: Path) -> bool:
    """Skip per-doc Layer B when only a single ABBYY-style dump exists."""
    if not cache_dir.is_dir():
        return False
    txts = [
        x for x in cache_dir.glob("*.txt")
        if x.is_file() and "scripture_index" not in x.name and "talk_index" not in x.name
    ]
    if len(txts) != 1:
        return False
    return "abbyy" in txts[0].name.lower()


def flat_cache_txt_missing(leaves: list[dict]) -> list[dict]:
    """Layer B: TOC leaf href stem must exist as {stem}.txt under the matching cache dir."""
    missing: list[dict] = []
    for row in leaves:
        cid = row["collection_id"]
        href = row.get("href") or ""
        if not href.endswith(".html"):
            continue
        stem = Path(href).stem

        if cid == "ancient_texts":
            found = False
            hit_path = ""
            for sub in ANCIENT_TEXTS_CACHE_DIRS:
                p = CACHE / sub / f"{stem}.txt"
                if p.is_file():
                    found = True
                    hit_path = str(p.relative_to(REPO))
                    break
            if not found:
                missing.append({
                    "collection_id": cid,
                    "doc_id": row["doc_id"],
                    "href": href,
                    "expected_txt_any": [str((CACHE / s / f"{stem}.txt").relative_to(REPO)) for s in ANCIENT_TEXTS_CACHE_DIRS],
                })
            continue

        cache_key = TOC_TO_CACHE_DIR.get(cid)
        if not cache_key:
            continue
        cache_sub = CACHE / cache_key
        if cid in ("millennial_star", "times_and_seasons") and cache_sub.exists():
            if _monolithic_periodical_skip(cache_sub):
                continue
        txt = cache_sub / f"{stem}.txt"
        if not txt.is_file():
            missing.append({
                "collection_id": cid,
                "doc_id": row["doc_id"],
                "href": href,
                "expected_txt": str(txt.relative_to(REPO)),
            })
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit TOC vs embedding passage loaders")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if Layer A (zero passages) or Layer B (missing per-doc cache .txt where applicable)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_JSON,
        help=f"JSON output path (default: {OUT_JSON})",
    )
    args = parser.parse_args()

    summary: dict = {"skipped": False, "reason": ""}
    report: dict = {"summary": summary}

    if not SOURCE_TOC.exists():
        summary["skipped"] = True
        summary["reason"] = f"missing {SOURCE_TOC.relative_to(REPO)}"
        print(json.dumps(summary, indent=2))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0

    catalog = load_catalog()
    if not catalog:
        summary["skipped"] = True
        summary["reason"] = "verse catalog missing (lds_pipeline/cache/verse_catalog.json or standard_works/verse_catalog.json)"
        print(json.dumps(summary, indent=2))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0

    leaves = flatten_toc_leaves()
    toc_para_by_collection: dict[str, int] = defaultdict(int)
    for row in leaves:
        toc_para_by_collection[row["collection_id"]] += row["paragraphs"]

    passages: list[dict] = []
    load_err = ""
    try:
        load_all_sources = import_load_all_sources()
        buf = io.StringIO()
        with redirect_stdout(buf):
            passages = load_all_sources(catalog)
    except Exception as e:
        load_err = str(e)
        summary["skipped"] = True
        summary["reason"] = f"load_all_sources failed: {load_err}"

    by_source = Counter(p.get("source", "") for p in passages)

    collection_rows = []
    collection_no_passages: list[str] = []
    for cid, para_sum in sorted(toc_para_by_collection.items()):
        pcount = passage_count_for_toc_collection(cid, by_source)
        src_keys = TOC_TO_PASSAGE_SOURCES.get(cid, [cid])
        row = {
            "collection_id": cid,
            "toc_paragraphs": para_sum,
            "embedding_passages": pcount,
            "embedding_source_keys": src_keys,
            "collection_no_passages": para_sum > 0 and pcount == 0,
        }
        collection_rows.append(row)
        if row["collection_no_passages"]:
            collection_no_passages.append(cid)

    cache_txt_missing = flat_cache_txt_missing(leaves)

    summary.update({
        "skipped": bool(summary.get("skipped")),
        "toc_leaf_docs": len(leaves),
        "embedding_passage_total": len(passages),
        "embedding_passage_by_source": dict(sorted(by_source.items())),
        "collections_with_toc_but_zero_passages": collection_no_passages,
        "missing_cache_txt_docs": len(cache_txt_missing),
    })
    if load_err:
        summary["load_error"] = load_err

    report["summary"] = summary
    report["collections"] = collection_rows
    report["missing_cache_txt"] = cache_txt_missing[:800]
    if len(cache_txt_missing) > 800:
        report["missing_cache_txt_truncated"] = True

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {args.out.relative_to(REPO)}")
    print(f"  TOC leaf docs: {len(leaves)}")
    print(f"  Embedding passages: {len(passages)}")
    if collection_no_passages:
        print(f"  WARN collections (TOC paras > 0, zero passages): {', '.join(collection_no_passages)}")
    if cache_txt_missing:
        print(f"  WARN TOC docs missing expected cache .txt: {len(cache_txt_missing)} (see JSON)")

    if args.strict and not summary.get("skipped"):
        if collection_no_passages or cache_txt_missing:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
