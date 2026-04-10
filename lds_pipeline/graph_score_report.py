#!/usr/bin/env python3
"""Histogram of edge weights in chapter *_graph.json (diagnostics for tuning MIN_SCORE)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CH = REPO / "library" / "chapters"
OUT = REPO / "diagnostics" / "graph_score_histogram.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins", type=int, default=20, help="Quantize to N bins in [0,1]")
    args = ap.parse_args()

    ctr: Counter[float] = Counter()
    n_edges = 0
    for gf in sorted(CH.glob("*_graph.json")):
        try:
            g = json.loads(gf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for e in g.get("edges", []) or []:
            w = float(e.get("w") or 0)
            if w <= 0:
                continue
            n_edges += 1
            b = round(w * args.bins) / args.bins
            ctr[b] += 1

    doc = {
        "chapter_graph_files": len(list(CH.glob("*_graph.json"))),
        "edges_with_positive_w": n_edges,
        "histogram": {str(k): ctr[k] for k in sorted(ctr.keys())},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} — {n_edges} edges")


if __name__ == "__main__":
    main()
