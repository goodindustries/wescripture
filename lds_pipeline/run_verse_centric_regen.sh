#!/usr/bin/env bash
# Full verse-centric offline regen after cache/HTML alignment.
# Passage embed + correlate is often 1–3+ hours on CPU with a full corpus; use nohup or run overnight.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p diagnostics

echo "== 1. Export shipped HTML paragraphs into lds_pipeline/cache (flat .txt) =="
python3 lds_pipeline/export_library_sources_to_embedding_cache.py --apply

echo "== 2. Dense correlate (rebuild passage vectors if counts changed) =="
python3 lds_pipeline/correlate_embeddings.py --rebuild --deep-books John

echo "== 3. Chapter graphs (higher cap for John) =="
python3 lds_pipeline/build_graph.py --deep-books john

echo "== 4. Paragraph reverse index + verse discovery + coverage =="
python3 lds_pipeline/build_source_links.py
python3 lds_pipeline/build_verse_discovery.py
python3 lds_pipeline/build_verse_coverage.py --quiet 2>/dev/null || true

echo "== 5. Strict embedding / TOC gate =="
python3 lds_pipeline/audit_embedding_corpus_gaps.py --strict || true

echo "Done. Ship: git add -A && git commit && git push && npx netlify-cli deploy --prod --dir ."
