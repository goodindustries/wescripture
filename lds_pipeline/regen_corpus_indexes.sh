#!/usr/bin/env bash
# Regenerate downstream indexes after graph or source corpus changes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 lds_pipeline/build_graph.py
python3 lds_pipeline/build_source_links.py
python3 lds_pipeline/build_verse_discovery.py
python3 lds_pipeline/build_verse_coverage.py --quiet 2>/dev/null || true
echo "regen_corpus_indexes: done"
