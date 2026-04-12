# Corpus index regen order

When **chapter graphs**, **source HTML**, or **correlation JSON** change, rebuild downstream artifacts in this order:

0. **Optional — align cache text with shipped HTML** (same `p.source-para` boundaries as the reader):  
   [`lds_pipeline/export_library_sources_to_embedding_cache.py`](../lds_pipeline/export_library_sources_to_embedding_cache.py) (`--apply`), then re-run dense embeddings / correlations as needed.

0b. **Gate — TOC vs embedding loaders** (environments that claim a full embedding corpus):  
   `python3 lds_pipeline/audit_embedding_corpus_gaps.py --strict`  
   Optional CI: GitHub Actions workflow `embedding-audit.yml` (when `lds_pipeline/cache/` including `verse_catalog.json` is present in the runner).

1. **Dense correlations** (after `load_all_sources` / passage embeddings):  
   [`lds_pipeline/correlate_embeddings.py`](../lds_pipeline/correlate_embeddings.py) (optional `--deep-books John` for expanded top-N on pilot books)

2. **Chapter graphs** (verse ↔ passage edges, `d`/`p` on source nodes):  
   [`lds_pipeline/build_graph.py`](../lds_pipeline/build_graph.py) (optional `--deep-books john` for higher per-verse cap on those chapters)

3. **Reverse index** (paragraph → verses):  
   [`lds_pipeline/build_source_links.py`](../lds_pipeline/build_source_links.py)

4. **Verse discovery** (cross-tradition rows):  
   [`lds_pipeline/build_verse_discovery.py`](../lds_pipeline/build_verse_discovery.py)

5. **Coverage / metrics** (optional):  
   [`lds_pipeline/build_verse_coverage.py`](../lds_pipeline/build_verse_coverage.py)

Wrapper script: [`lds_pipeline/regen_corpus_indexes.sh`](../lds_pipeline/regen_corpus_indexes.sh)

After cache sync / before correlating, audit whether shipped `source_toc` docs are represented in `load_all_sources()` (and flat per-doc `.txt` where Layer B applies):  
`python3 lds_pipeline/audit_embedding_corpus_gaps.py` → [`diagnostics/embedding_loader_gaps.json`](../diagnostics/embedding_loader_gaps.json) (use `--strict` to fail on gaps).

**Documented regen order (verse-centric recall):** export paragraphs (optional) → `correlate_embeddings` → `build_graph` → `build_verse_discovery` → deploy.
