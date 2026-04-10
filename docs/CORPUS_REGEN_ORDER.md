# Corpus index regen order

When **chapter graphs**, **source HTML**, or **correlation JSON** change, rebuild downstream artifacts in this order:

1. **Chapter graphs** (verse ↔ passage edges, `d`/`p` on source nodes):  
   [`lds_pipeline/build_graph.py`](../lds_pipeline/build_graph.py)

2. **Reverse index** (paragraph → verses):  
   [`lds_pipeline/build_source_links.py`](../lds_pipeline/build_source_links.py)

3. **Verse discovery** (cross-tradition rows):  
   [`lds_pipeline/build_verse_discovery.py`](../lds_pipeline/build_verse_discovery.py)

4. **Coverage / metrics** (optional):  
   [`lds_pipeline/build_verse_coverage.py`](../lds_pipeline/build_verse_coverage.py)

Wrapper script: [`lds_pipeline/regen_corpus_indexes.sh`](../lds_pipeline/regen_corpus_indexes.sh)
