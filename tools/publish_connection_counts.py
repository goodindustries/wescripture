#!/usr/bin/env python3
"""
Publish full connection-count tables for the website.

Outputs (repo-relative):
  - library/published/verse_connection_counts.tsv
  - library/published/morsel_connection_counts.tsv
  - library/published/connection_thresholds.json

Notes:
  - Verse counts are computed from chapter graph files (already filtered by build_graph --min-score).
  - Morsel counts are computed from library/source_links.json (reverse index of graph edges).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CHAPTERS = REPO / "library" / "chapters"
SOURCE_LINKS = REPO / "library" / "source_links.json"
OUT_DIR = REPO / "library" / "published"


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Verse counts: count edges per verse_ref across all graphs.
    verse_counts: Counter[str] = Counter()
    verse_seen: set[str] = set()

    graph_files = sorted(CHAPTERS.glob("*_graph.json"))
    for gf in graph_files:
        try:
            g = load_json(gf)
        except Exception:
            continue

        nodes = g.get("nodes", []) or []
        edges = g.get("edges", []) or []

        verse_nodes = {}
        # Verse nodes in graphs reliably include verse number, but not always bk/ch.
        # Derive bk/ch from filename stem (e.g. genesis_1_graph.json).
        stem = gf.stem.replace("_graph", "")
        parts = stem.rsplit("_", 1)
        file_ch = int(parts[1]) if (len(parts) == 2 and parts[1].isdigit()) else 0
        file_bk = parts[0].replace("_", " ").title() if file_ch else ""

        for n in nodes:
            if n.get("t") != "v":
                continue
            bk = n.get("bk") or file_bk or ""
            ch = n.get("ch") or file_ch or 0
            vn = n.get("n") or 0
            if not (bk and ch and vn):
                continue
            verse_ref = f"{bk} {int(ch)}:{int(vn)}"
            verse_nodes[n.get("id")] = verse_ref
            verse_seen.add(verse_ref)

        for e in edges:
            vref = verse_nodes.get(e.get("s"))
            if vref:
                verse_counts[vref] += 1

    # Include zero-count verses we saw in graphs.
    verse_rows = [(v, int(verse_counts.get(v, 0))) for v in sorted(verse_seen)]

    verse_out = OUT_DIR / "verse_connection_counts.tsv"
    verse_out.write_text(
        "# verse_ref\tconnections\n"
        "# source=library/chapters/*_graph.json\n"
        "# threshold=build_graph.MIN_SCORE (default 0.25 unless graphs were rebuilt with --min-score)\n"
        + "\n".join(f"{v}\t{n}" for v, n in verse_rows)
        + "\n",
        encoding="utf-8",
    )

    # Morsel counts: number of verse refs per (doc_id, para_idx) from reverse index.
    morsel_rows: list[tuple[str, str, int]] = []
    if SOURCE_LINKS.exists():
        sl = load_json(SOURCE_LINKS)
        for doc_id, paras in (sl or {}).items():
            if not isinstance(paras, dict):
                continue
            for para_idx, refs in paras.items():
                if not refs:
                    continue
                morsel_rows.append((str(doc_id), str(para_idx), int(len(refs))))

    morsel_rows.sort(key=lambda x: (-x[2], x[0], int(x[1]) if x[1].isdigit() else x[1]))
    morsel_out = OUT_DIR / "morsel_connection_counts.tsv"
    morsel_out.write_text(
        "# doc_id\tpara_idx\tverses\n"
        "# source=library/source_links.json\n"
        "# threshold=build_graph.MIN_SCORE (default 0.25 unless graphs were rebuilt with --min-score)\n"
        + "\n".join(f"{d}\t{p}\t{n}" for d, p, n in morsel_rows)
        + "\n",
        encoding="utf-8",
    )

    thresholds = {
        "graph_min_score_default": 0.25,
        "verse_discovery_min_score_default": 0.40,
        "notes": [
            "Graph edges are filtered in lds_pipeline/build_graph.py by --min-score (default 0.25).",
            "Verse discovery further filters graph edges in lds_pipeline/build_verse_discovery.py by --min-score (default 0.40).",
            "These published tables are counts; they do not include per-link score values.",
        ],
        "outputs": {
            "verse_connection_counts_tsv": "library/published/verse_connection_counts.tsv",
            "morsel_connection_counts_tsv": "library/published/morsel_connection_counts.tsv",
        },
    }
    (OUT_DIR / "connection_thresholds.json").write_text(
        json.dumps(thresholds, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {verse_out} ({len(verse_rows):,} verses)")
    print(f"Wrote {morsel_out} ({len(morsel_rows):,} morsels)")
    print(f"Wrote {OUT_DIR/'connection_thresholds.json'}")


if __name__ == "__main__":
    main()

