#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from source_registry import SourceRecord, registry


REPO = Path(__file__).resolve().parent.parent
LIBRARY = REPO / "library"
TOC = LIBRARY / "source_toc.json"
CACHE = REPO / "lds_pipeline" / "cache"
REPORT_DIR = REPO / "lds_pipeline" / "reports"
OUT_JSON = REPORT_DIR / "missing_corpus_report.json"
OUT_TXT = REPORT_DIR / "missing_corpus_report.txt"


def slugify(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def flatten_toc_doc_ids(toc_payload: list[dict]) -> set[str]:
    out: set[str] = set()
    for coll in toc_payload or []:
        items = coll.get("items") or []
        for it in items:
            if it.get("type") == "group":
                for leaf in it.get("items") or []:
                    if leaf.get("id"):
                        out.add(str(leaf["id"]))
            else:
                if it.get("id"):
                    out.add(str(it["id"]))
    return out


def expected_linkonly_doc_id(r: SourceRecord) -> str:
    return f"external_links:{slugify(r.id)}"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    regs = registry()

    toc_ids: set[str] = set()
    if TOC.exists():
        try:
            toc_ids = flatten_toc_doc_ids(json.loads(TOC.read_text(encoding="utf-8")))
        except Exception:
            toc_ids = set()

    rows = []
    for r in regs:
        row = {
            "id": r.id,
            "title": r.title,
            "author": r.author,
            "year": r.year,
            "canonical_url": r.canonical_url,
            "license_type": r.license_type,
            "license_url": r.license_url,
            "redistributable": r.redistributable,
            "ingest_mode": r.ingest_mode,
            "ingest_group": r.ingest_group,
        }

        if r.ingest_mode == "ingest":
            exists = False
            expected = None
            if r.cache_relpath:
                expected = str((CACHE / r.cache_relpath).relative_to(REPO))
                exists = (CACHE / r.cache_relpath).exists()
            row.update({"expected_cache_path": expected, "present": exists})
        else:
            did = expected_linkonly_doc_id(r)
            row.update({"expected_toc_doc_id": did, "present": did in toc_ids})

        rows.append(row)

    out = {
        "generated_by": "audit_missing_corpus.py",
        "registry_count": len(regs),
        "toc_present": TOC.exists(),
        "rows": rows,
    }

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("Missing corpus report (registry vs repo)")
    lines.append(f"registry_count: {len(regs)}")
    lines.append(f"source_toc_present: {TOC.exists()}")
    lines.append("")
    missing = [r for r in rows if not r.get("present")]
    lines.append(f"missing: {len(missing)}")
    for r in missing[:200]:
        lines.append(f"- {r['id']} ({r['ingest_mode']}) — {r.get('expected_cache_path') or r.get('expected_toc_doc_id')}")
    if len(missing) > 200:
        lines.append(f"... truncated ({len(missing) - 200} more)")
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_JSON.relative_to(REPO)}")
    print(f"Wrote {OUT_TXT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

