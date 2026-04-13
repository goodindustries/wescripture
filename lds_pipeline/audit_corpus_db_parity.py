#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "library"


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _get(url: str, key: str) -> object:
    h = {
        "apikey": key,
        "authorization": f"Bearer {key}",
        "accept": "application/json",
    }
    r = urllib.request.Request(url, headers=h, method="GET")
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


_TAG_RE = re.compile(r"<[^>]+>")
_PARA_RE = re.compile(r'<p[^>]*class="[^"]*source-para[^"]*"[^>]*>(.*?)</p>', re.I | re.S)


def strip_tags(html_fragment: str) -> str:
    t = _TAG_RE.sub(" ", html_fragment)
    t = unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def text_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:24]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-docs", type=int, default=20)
    args = ap.parse_args()

    base = _env("SUPABASE_URL").rstrip("/")
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not key:
        raise SystemExit("Missing env: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    toc_path = LIB / "source_toc.json"
    if not toc_path.exists():
        raise SystemExit("Missing library/source_toc.json")
    toc = json.loads(toc_path.read_text(encoding="utf-8"))

    leaf_docs = []
    for coll in toc:
        for it in coll.get("items") or []:
            docs = it.get("items") if it.get("type") == "group" else [it]
            for d in docs or []:
                if d.get("id") and d.get("href"):
                    leaf_docs.append({"id": d["id"], "href": d["href"]})

    db_sources = _get(base + "/rest/v1/corpus_sources?select=id", key)
    db_paras = _get(base + "/rest/v1/corpus_paragraphs?select=source_id", key)

    sources_n = len(db_sources) if isinstance(db_sources, list) else 0
    paras_n = len(db_paras) if isinstance(db_paras, list) else 0

    mismatches = []
    for row in leaf_docs[: max(1, args.sample_docs)]:
        doc_id = str(row["id"])
        href = str(row["href"])
        if not href.endswith(".html"):
            continue
        fp = LIB / href
        if not fp.exists():
            continue
        raw = fp.read_text(encoding="utf-8", errors="replace")
        paras = [strip_tags(p) for p in _PARA_RE.findall(raw)]

        q = urllib.parse.urlencode(
            {
                "select": "para_idx,text_hash",
                "source_id": f"eq.{doc_id}",
                "order": "para_idx.asc",
                "limit": "5",
            }
        )
        db = _get(base + "/rest/v1/corpus_paragraphs?" + q, key)
        if not isinstance(db, list) or not db:
            continue
        for i in range(min(5, len(paras), len(db))):
            file_h = text_hash(paras[i])
            db_h = str(db[i].get("text_hash") or "")
            if file_h != db_h:
                mismatches.append({"doc_id": doc_id, "para_idx": i + 1, "file": file_h, "db": db_h})
                break

    report = {
        "file_leaf_docs": len(leaf_docs),
        "db_sources": sources_n,
        "db_paragraphs": paras_n,
        "sample_docs_checked": min(len(leaf_docs), max(1, args.sample_docs)),
        "sample_mismatches": mismatches[:50],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())

