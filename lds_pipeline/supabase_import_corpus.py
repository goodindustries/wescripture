#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error
from html import unescape
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "library"
CACHE = REPO / "lds_pipeline" / "cache"


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _rest_url(base: str, table: str, query: str = "") -> str:
    base = base.rstrip("/")
    url = base + "/rest/v1/" + table
    return url + (("?" + query) if query else "")


def _req(method: str, url: str, key: str, body: bytes | None = None, headers: dict | None = None) -> tuple[int, str]:
    h = {
        "apikey": key,
        "authorization": f"Bearer {key}",
        "accept": "application/json",
        "content-type": "application/json",
    }
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        return int(getattr(e, "code", 0) or 0), raw


def upsert_rows(base_url: str, key: str, table: str, rows: list[dict], *, on_conflict: str) -> None:
    if not rows:
        return
    q = urllib.parse.urlencode({"on_conflict": on_conflict})
    url = _rest_url(base_url, table, q)
    status, text = _req(
        "POST",
        url,
        key,
        body=json.dumps(rows, ensure_ascii=False).encode("utf-8"),
        headers={"prefer": "resolution=merge-duplicates,return=minimal"},
    )
    if status not in (200, 201, 204):
        raise RuntimeError(f"upsert {table} failed ({status}): {text[:400]}")


_TAG_RE = re.compile(r"<[^>]+>")
_PARA_RE = re.compile(r'<p[^>]*class="[^"]*source-para[^"]*"[^>]*>(.*?)</p>', re.I | re.S)


def strip_tags(html_fragment: str) -> str:
    t = _TAG_RE.sub(" ", html_fragment)
    t = unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def read_source_paragraphs(html_path: Path) -> list[str]:
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    paras = _PARA_RE.findall(raw)
    out = []
    for p in paras:
        text = strip_tags(p)
        if text:
            out.append(text)
    return out


def text_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:24]


def import_sources(base_url: str, key: str, *, limit_collections: set[str] | None = None, skip_paragraphs: bool = False) -> None:
    toc_path = LIB / "source_toc.json"
    if not toc_path.exists():
        print("SKIP: library/source_toc.json missing")
        return
    toc = json.loads(toc_path.read_text(encoding="utf-8"))

    collections: list[dict] = []
    sources: list[dict] = []

    for c_idx, coll in enumerate(toc):
        coll_id = str(coll.get("id") or "")
        if not coll_id:
            continue
        if limit_collections and coll_id not in limit_collections:
            continue
        collections.append(
            {
                "id": coll_id,
                "label": str(coll.get("label") or coll_id),
                "description": str(coll.get("description") or ""),
                "sort": 1000 + c_idx,
            }
        )

        items = coll.get("items") or []
        for it in items:
            docs = it.get("items") if it.get("type") == "group" else [it]
            gid = str(it.get("id") or "") if it.get("type") == "group" else ""
            glabel = str(it.get("label") or "") if it.get("type") == "group" else ""
            gmeta = str(it.get("meta") or "") if it.get("type") == "group" else ""
            for d in docs or []:
                did = str(d.get("id") or "")
                href = str(d.get("href") or "")
                if not did:
                    continue
                external = str(d.get("external_url") or "")
                ingest_mode = "link_only" if external else "ingest"
                sources.append(
                    {
                        "id": did,
                        "collection_id": coll_id,
                        "title": str(d.get("label") or did),
                        "author": "",
                        "year": None,
                        "canonical_url": external,
                        "license_type": "unknown",
                        "license_url": None,
                        "redistributable": True,
                        "ingest_mode": ingest_mode,
                        "group_id": gid or None,
                        "group_label": glabel or None,
                        "group_meta": gmeta or None,
                        "source_meta": str(d.get("meta") or ""),
                    }
                )

    upsert_rows(base_url, key, "corpus_collections", collections, on_conflict="id")
    upsert_rows(base_url, key, "corpus_sources", sources, on_conflict="id")

    if skip_paragraphs:
        return

    # Second pass: paragraphs (requires sources already present for FK).
    paragraphs: list[dict] = []
    for coll in toc:
        coll_id = str(coll.get("id") or "")
        if limit_collections and coll_id not in limit_collections:
            continue
        for it in coll.get("items") or []:
            docs = it.get("items") if it.get("type") == "group" else [it]
            for d in docs or []:
                did = str(d.get("id") or "")
                href = str(d.get("href") or "")
                if not did or not href or not href.endswith(".html"):
                    continue
                external = str(d.get("external_url") or "")
                if external:
                    continue  # link_only
                fp = LIB / href
                if not fp.exists():
                    continue
                paras = read_source_paragraphs(fp)
                for idx, t in enumerate(paras, start=1):
                    paragraphs.append({"source_id": did, "para_idx": idx, "text": t, "text_hash": text_hash(t)})
                if len(paragraphs) >= 1500:
                    upsert_rows(base_url, key, "corpus_paragraphs", paragraphs, on_conflict="source_id,para_idx")
                    print(f"upsert corpus_paragraphs: +{len(paragraphs)}")
                    paragraphs = []
    if paragraphs:
        upsert_rows(base_url, key, "corpus_paragraphs", paragraphs, on_conflict="source_id,para_idx")
        print(f"upsert corpus_paragraphs: +{len(paragraphs)}")


def import_source_links(base_url: str, key: str) -> None:
    path = LIB / "source_links.json"
    if not path.exists():
        print("SKIP: library/source_links.json missing")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for doc_id, paras in (data or {}).items():
        for p_idx, refs in (paras or {}).items():
            try:
                i = int(p_idx)
            except Exception:
                continue
            rows.append({"source_id": str(doc_id), "para_idx": i, "refs": refs or []})
            if len(rows) >= 2000:
                upsert_rows(base_url, key, "corpus_source_links", rows, on_conflict="source_id,para_idx")
                print(f"upsert corpus_source_links: +{len(rows)}")
                rows = []
    if rows:
        upsert_rows(base_url, key, "corpus_source_links", rows, on_conflict="source_id,para_idx")
        print(f"upsert corpus_source_links: +{len(rows)}")


def import_source_citations(base_url: str, key: str) -> None:
    path = LIB / "source_citations.json"
    if not path.exists():
        print("SKIP: library/source_citations.json missing")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for doc_id, paras in (data or {}).items():
        for p_idx, refs in (paras or {}).items():
            try:
                i = int(p_idx)
            except Exception:
                continue
            rows.append({"source_id": str(doc_id), "para_idx": i, "refs": refs or []})
            if len(rows) >= 2000:
                upsert_rows(base_url, key, "corpus_source_citations", rows, on_conflict="source_id,para_idx")
                print(f"upsert corpus_source_citations: +{len(rows)}")
                rows = []
    if rows:
        upsert_rows(base_url, key, "corpus_source_citations", rows, on_conflict="source_id,para_idx")
        print(f"upsert corpus_source_citations: +{len(rows)}")


def import_chapter_graphs(base_url: str, key: str, *, max_files: int | None = None) -> None:
    ch_dir = LIB / "chapters"
    if not ch_dir.exists():
        print("SKIP: library/chapters missing")
        return
    rows: list[dict] = []
    n = 0
    for fp in sorted(ch_dir.glob("*_graph.json")):
        n += 1
        if max_files and n > max_files:
            break
        try:
            graph = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        chapter_id = fp.stem.replace("_graph", "")
        rows.append({"chapter_id": chapter_id, "graph": graph})
        if len(rows) >= 100:
            upsert_rows(base_url, key, "corpus_chapter_graphs", rows, on_conflict="chapter_id")
            print(f"upsert corpus_chapter_graphs: +{len(rows)}")
            rows = []
    if rows:
        upsert_rows(base_url, key, "corpus_chapter_graphs", rows, on_conflict="chapter_id")
        print(f"upsert corpus_chapter_graphs: +{len(rows)}")


def import_verse_catalog(base_url: str, key: str) -> None:
    path = CACHE / "verse_catalog.json"
    if not path.exists():
        path = CACHE / "standard_works" / "verse_catalog.json"
    if not path.exists():
        print("SKIP: verse catalog missing")
        return
    catalog = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for v in catalog or []:
        book = str(v.get("book") or "")
        ch = v.get("chapter")
        ve = v.get("verse")
        text = str(v.get("text") or "")
        if not book or not isinstance(ch, int) or not isinstance(ve, int) or not text:
            continue
        verse_key = f"{book}_{ch}_{ve}"
        rows.append(
            {
                "verse_key": verse_key,
                "book": book,
                "chapter": ch,
                "verse": ve,
                "text": text,
                "volume": str(v.get("volume") or "") or None,
            }
        )
        if len(rows) >= 2000:
            upsert_rows(base_url, key, "corpus_verse_catalog", rows, on_conflict="verse_key")
            print(f"upsert corpus_verse_catalog: +{len(rows)}")
            rows = []
    if rows:
        upsert_rows(base_url, key, "corpus_verse_catalog", rows, on_conflict="verse_key")
        print(f"upsert corpus_verse_catalog: +{len(rows)}")


def import_correlations(base_url: str, key: str, *, max_files: int | None = None) -> None:
    corr = CACHE / "correlations"
    if not corr.exists():
        print("SKIP: cache/correlations missing")
        return
    rows: list[dict] = []
    n = 0
    for fp in sorted(corr.glob("*.json")):
        n += 1
        if max_files and n > max_files:
            break
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        verse_key = fp.stem
        engine = str(data.get("engine") or "sentence_transformers")
        matches = data.get("matches") or []
        rows.append({"verse_key": verse_key, "engine": engine, "matches_json": matches})
        if len(rows) >= 400:
            upsert_rows(base_url, key, "corpus_correlations", rows, on_conflict="verse_key,engine")
            print(f"upsert corpus_correlations: +{len(rows)}")
            rows = []
    if rows:
        upsert_rows(base_url, key, "corpus_correlations", rows, on_conflict="verse_key,engine")
        print(f"upsert corpus_correlations: +{len(rows)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collections", nargs="*", help="Only import these source collection IDs")
    ap.add_argument("--skip-paragraphs", action="store_true")
    ap.add_argument("--skip-links", action="store_true")
    ap.add_argument("--skip-citations", action="store_true")
    ap.add_argument("--skip-graphs", action="store_true")
    ap.add_argument("--skip-verse-catalog", action="store_true")
    ap.add_argument("--skip-correlations", action="store_true")
    ap.add_argument("--max-graph-files", type=int, default=None)
    ap.add_argument("--max-correlation-files", type=int, default=None)
    args = ap.parse_args()

    base_url = _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not base_url or not key:
        raise SystemExit("Missing env: SUPABASE_URL and/or SUPABASE_SERVICE_ROLE_KEY")

    limit = set(args.collections) if args.collections else None

    print("Import: sources + paragraphs")
    import_sources(base_url, key, limit_collections=limit, skip_paragraphs=args.skip_paragraphs)
    if not args.skip_links:
        print("Import: source_links")
        import_source_links(base_url, key)
    if not args.skip_citations:
        print("Import: source_citations")
        import_source_citations(base_url, key)
    if not args.skip_graphs:
        print("Import: chapter_graphs")
        import_chapter_graphs(base_url, key, max_files=args.max_graph_files)
    if not args.skip_verse_catalog:
        print("Import: verse_catalog")
        import_verse_catalog(base_url, key)
    if not args.skip_correlations:
        print("Import: correlations")
        import_correlations(base_url, key, max_files=args.max_correlation_files)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

