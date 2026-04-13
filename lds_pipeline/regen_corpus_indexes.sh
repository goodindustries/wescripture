#!/usr/bin/env bash
# Regenerate downstream indexes after graph or source corpus changes.
# Full verse-centric pipeline (when correlations change): correlate_embeddings → build_graph → this script.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 lds_pipeline/build_graph.py
python3 lds_pipeline/build_source_links.py
python3 lds_pipeline/build_verse_discovery.py
python3 lds_pipeline/build_verse_coverage.py --quiet 2>/dev/null || true
# Optional: library/chapters/*_lexstudies.json (set REGEN_LEX_STUDIES=1; add --ollama when Ollama is running)
if [[ "${REGEN_LEX_STUDIES:-}" == "1" ]]; then
  python3 lds_pipeline/build_lex_studies.py --all ${REGEN_LEX_STUDIES_FLAGS:-}
fi
echo "regen_corpus_indexes: done"
