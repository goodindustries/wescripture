#!/usr/bin/env python3
"""
Build a JSON map of library corpus HTML (source_toc), quality heuristics,
embedding-pipeline cache coverage, and per-verse correlation completeness.

Writes: lds_pipeline/reports/corpus_resource_map.json

  python3 lds_pipeline/audit_corpus_resources.py
  python3 lds_pipeline/audit_corpus_resources.py --no-html   # skip per-file HTML scan (TOC only)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "library"
TOC_PATH = LIB / "source_toc.json"
CACHE = REPO / "lds_pipeline" / "cache"
CORR_DIR = CACHE / "correlations"
EMB_DIR = CACHE / "embeddings_dense"
CATALOG_PRIMARY = CACHE / "verse_catalog.json"
CATALOG_SW = CACHE / "standard_works" / "verse_catalog.json"
REPORT_DIR = REPO / "lds_pipeline" / "reports"
REPORT_JSON = REPORT_DIR / "corpus_resource_map.json"

# Same dirs as correlate_embeddings.load_all_sources (cache-relative)
EMBEDDING_SOURCE_DIRS: list[tuple[str, str]] = [
    ("jd", "journal_of_discourses"),
    ("sefaria", "sefaria"),
    ("general_conference", "general_conference"),
    ("gutenberg_lds", "gutenberg_lds"),
    ("church_fathers", "church_fathers"),
    ("ancient_myths", "ancient_myths"),
    ("hoc", "history_of_church"),
    ("joseph_smith_papers", "joseph_smith_papers"),
    ("donaldson", "donaldson"),
    ("times_and_seasons", "times_and_seasons"),
    ("millennial_star", "millennial_star"),
    ("pioneer_journals", "pioneer_journals"),
    ("pseudepigrapha", "pseudepigrapha"),
    ("apocrypha", "apocrypha"),
    ("nag_hammadi", "nag_hammadi"),
    ("dead_sea_scrolls", "dead_sea_scrolls"),
    ("bh_roberts", "bh_roberts"),
    ("nibley", "nibley"),
    ("nauvoo_theology", "nauvoo_theology"),
    ("jst", "jst"),
]

_HIGH_NON_ASCII = re.compile(r"[^\x00-\x7F]")
_BOILER = re.compile(
    r"(transcribed from|editor'?s note|ocr\s|digitized by|disclaimer:|"
    r"\[illustration\]|\[image\]|table of contents)",
    re.I,
)
_TAG_STRIP = re.compile(r"<[^>]+>")


def walk_toc(nodes, out: list[dict]) -> None:
    if isinstance(nodes, list):
        for n in nodes:
            walk_toc(n, out)
        return
    if not isinstance(nodes, dict):
        return
    href = nodes.get("href")
    if isinstance(href, str) and href.endswith(".html"):
        doc_id = nodes.get("id", "")
        out.append(
            {
                "id": doc_id,
                "href": href,
                "label": (nodes.get("label") or "")[:200],
                "toc_paragraphs": nodes.get("paragraphs"),
                "type": nodes.get("type"),
            }
        )
    for v in nodes.values():
        if isinstance(v, (list, dict)):
            walk_toc(v, out)


def strip_html_inner(fragment: str) -> str:
    return _TAG_STRIP.sub(" ", fragment)


def ocr_ok(text: str) -> bool:
    non_ascii = len(_HIGH_NON_ASCII.findall(text))
    return non_ascii / max(len(text), 1) < 0.12


def analyze_html(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    n_para = len(re.findall(r'class="[^"]*source-para', raw))
    m = re.search(r'<p[^>]*class="[^"]*source-para[^"]*"[^>]*>', raw, re.I)
    preamble = raw[: m.start()] if m else raw[:8000]
    paras_html = re.findall(
        r'<p[^>]*class="[^"]*source-para[^"]*"[^>]*>(.*?)</p>',
        raw,
        re.S | re.I,
    )
    bodies = [strip_html_inner(p) for p in paras_html[:12]]
    joined = "\n".join(bodies)
    stripped_ok = (
        "\ufffd" not in joined
        and "\x00" not in raw
        and ocr_ok(joined)
        and joined.count("&nbsp;") < len(joined) // 40
    )
    intro_issues: list[str] = []
    if len(preamble) > 12000:
        intro_issues.append("long_preamble_before_first_para")
    if _BOILER.search(preamble[:12000] or ""):
        intro_issues.append("possible_boilerplate_in_preamble")
    if paras_html:
        first_plain = strip_html_inner(paras_html[0])[:400]
        if _BOILER.search(first_plain):
            intro_issues.append("boilerplate_in_first_para")

    return {
        "bytes": path.stat().st_size,
        "source_para_count": n_para,
        "paragraphized": n_para >= 1,
        "stripped_heuristic_ok": stripped_ok,
        "intro_cleanup_ok": len(intro_issues) == 0,
        "intro_flags": intro_issues,
    }


def count_txt_files(d: Path) -> int:
    if not d.is_dir():
        return 0
    return sum(1 for f in d.rglob("*.txt") if f.is_file())


def cache_artifact_count(dirname: str) -> tuple[int, str]:
    """Return (count, kind) for correlate_embeddings cache inputs."""
    p = CACHE / dirname
    if not p.exists():
        return 0, "missing"
    if dirname == "sefaria":
        n = len(list(p.glob("links_*.json")))
        return n, "links_json"
    if dirname == "donaldson":
        f = p / "corpus.json"
        return (1 if f.is_file() else 0), "corpus_json"
    return count_txt_files(p), "txt"


def embedding_cache_report() -> dict:
    rows = []
    for dirname, source_key in EMBEDDING_SOURCE_DIRS:
        n, kind = cache_artifact_count(dirname)
        p = CACHE / dirname
        exists = p.is_dir() or (dirname == "donaldson" and (CACHE / "donaldson" / "corpus.json").is_file())
        rows.append(
            {
                "cache_dir": dirname,
                "source_key": source_key,
                "artifact_count": n,
                "artifact_kind": kind,
                "exists": exists,
            }
        )
    emb_meta = EMB_DIR / "passages_meta.pkl"
    emb_npy = EMB_DIR / "passages.npy"
    passage_cache: dict = {
        "passages_npy_exists": emb_npy.is_file(),
        "passages_meta_exists": emb_meta.exists(),
    }
    if emb_meta.is_file() and emb_npy.is_file():
        import pickle

        try:
            passage_cache["cached_passage_count"] = int(pickle.loads(emb_meta.read_bytes()))
        except Exception:
            passage_cache["cached_passage_count"] = None
    return {"source_dirs": rows, "dense_embedding_cache": passage_cache}


def scripture_vector_report(catalog: list[dict]) -> dict:
    missing_files: list[str] = []
    wrong_engine: list[str] = []
    ok = 0
    for v in catalog:
        book, ch, verse = v["book"], v["chapter"], v["verse"]
        key = f"{book}_{ch}_{verse}"
        fp = CORR_DIR / f"{key}.json"
        if not fp.is_file():
            missing_files.append(key)
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            missing_files.append(key)
            continue
        if data.get("engine") != "sentence_transformers":
            wrong_engine.append(key)
        else:
            ok += 1
    by_book = defaultdict(int)
    for k in missing_files:
        book = k.rsplit("_", 2)[0]
        by_book[book] += 1
    return {
        "catalog_verses": len(catalog),
        "correlation_files_ok": ok,
        "missing_correlation_file": len(missing_files),
        "wrong_engine": len(wrong_engine),
        "missing_sample": missing_files[:80],
        "missing_count_by_book": dict(sorted(by_book.items(), key=lambda x: -x[1])[:40]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-html", action="store_true", help="Skip reading each HTML body (faster)")
    args = ap.parse_args()

    if not TOC_PATH.is_file():
        print("ERROR: missing library/source_toc.json", file=sys.stderr)
        sys.exit(1)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    tree = json.loads(TOC_PATH.read_text(encoding="utf-8"))
    docs: list[dict] = []
    walk_toc(tree, docs)

    catalog_path = CATALOG_PRIMARY if CATALOG_PRIMARY.is_file() else CATALOG_SW
    catalog: list[dict] = []
    if catalog_path.is_file():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    html_rows: list[dict] = []
    summary = {
        "total_toc_html_docs": len(docs),
        "missing_files": 0,
        "not_paragraphized": 0,
        "stripped_heuristic_fail": 0,
        "intro_flags_nonzero": 0,
        "toc_paragraph_mismatch": 0,
    }

    for d in docs:
        href = d["href"]
        row = dict(d)
        fp = LIB / href
        if not fp.is_file():
            row["file_exists"] = False
            summary["missing_files"] += 1
            html_rows.append(row)
            continue
        row["file_exists"] = True
        if args.no_html:
            row["html_scan"] = "skipped"
            html_rows.append(row)
            continue
        try:
            ha = analyze_html(fp)
        except Exception as e:
            ha = {"error": str(e)}
            html_rows.append({**row, "html_scan": ha})
            continue
        row["html_scan"] = ha
        if not ha.get("paragraphized"):
            summary["not_paragraphized"] += 1
        if not ha.get("stripped_heuristic_ok", True):
            summary["stripped_heuristic_fail"] += 1
        if not ha.get("intro_cleanup_ok", True):
            summary["intro_flags_nonzero"] += 1
        tp = d.get("toc_paragraphs")
        if isinstance(tp, int) and tp > 0 and ha.get("source_para_count", 0) > 0:
            if abs(tp - ha["source_para_count"]) > max(3, int(0.15 * max(tp, ha["source_para_count"]))):
                row["toc_count_mismatch"] = True
                summary["toc_paragraph_mismatch"] += 1
        html_rows.append(row)

    emb_rep = embedding_cache_report()
    sv_rep = (
        scripture_vector_report(catalog)
        if catalog
        else {"error": "no verse catalog at cache/verse_catalog.json or cache/standard_works/verse_catalog.json"}
    )
    empty_cache = [r["source_key"] for r in emb_rep["source_dirs"] if r.get("artifact_count", 0) == 0]
    n_corr = sum(1 for _ in CORR_DIR.glob("*.json")) if CORR_DIR.is_dir() else 0
    gaps = {
        "verse_catalog_missing": not catalog_path.is_file(),
        "correlation_json_count": n_corr,
        "passage_embedding_cache_ready": bool(
            emb_rep["dense_embedding_cache"].get("passages_npy_exists")
            and emb_rep["dense_embedding_cache"].get("passages_meta_exists")
        ),
        "embedding_cache_dirs_with_zero_artifacts": empty_cache,
        "note": "Reader corpus lives under library/sources (HTML). correlate_embeddings.py reads lds_pipeline/cache/*.txt and API-built verse_catalog — not the HTML files directly.",
    }

    out = {
        "generated_by": "audit_corpus_resources.py",
        "paths": {
            "source_toc": str(TOC_PATH.relative_to(REPO)),
            "verse_catalog": str(catalog_path.relative_to(REPO)) if catalog_path.is_file() else None,
            "correlations_dir": str(CORR_DIR.relative_to(REPO)),
        },
        "summary": summary,
        "gaps": gaps,
        "embedding_pipeline_cache": emb_rep,
        "scripture_vectorization": sv_rep,
        "documents": html_rows,
    }

    REPORT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    missing_txt = REPORT_DIR / "corpus_missing_list.txt"
    lines = [
        "Corpus / vectorization gaps (see corpus_resource_map.json for full detail)",
        "",
    ]
    g = out.get("gaps") or {}
    lines.append(f"verse_catalog_missing: {g.get('verse_catalog_missing')}")
    lines.append(f"correlation_json_count: {g.get('correlation_json_count')}")
    lines.append(f"passage_embedding_cache_ready: {g.get('passage_embedding_cache_ready')}")
    z = g.get("embedding_cache_dirs_with_zero_artifacts") or []
    if z:
        lines.append(f"cache dirs with zero passage files (first 25): {', '.join(z[:25])}")
    sv = out.get("scripture_vectorization") or {}
    if "missing_correlation_file" in sv:
        lines.append(
            f"scripture verses missing dense correlation JSON: {sv['missing_correlation_file']} / {sv.get('catalog_verses', '?')}"
        )
    lines.append("")
    lines.append("Suggested ledger titles (handled by task_dispatch.py):")
    lines.append("  Corpus pipeline: run correlate_embeddings")
    lines.append("  Corpus pipeline: correlate_embeddings books   (notes: Genesis Exodus …)")
    lines.append("  Corpus maintenance: lint_source_paras")
    lines.append("  Corpus maintenance: add_para_ids_to_sources")
    lines.append("  Corpus audit: regenerate resource map")
    missing_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_JSON.relative_to(REPO)}")
    print(f"Wrote {missing_txt.relative_to(REPO)}")
    print(json.dumps(summary, indent=2))
    sv = out["scripture_vectorization"]
    if "catalog_verses" in sv:
        print(
            f"Scripture: {sv['correlation_files_ok']}/{sv['catalog_verses']} verses have dense correlation JSON"
        )


if __name__ == "__main__":
    main()
