# Morphology assets (lemma alignment for lex studies)

Pipeline scripts download upstream data into `lds_pipeline/cache/morphology/` (not committed) and emit per-chapter `*_lexstudies.json` under `library/chapters/`.

Verse **Key words** graph cards read the `study` field from those JSON files only (no `_words.json` excerpt mashup in the reader). To ship LLM prose, run `python3 lds_pipeline/build_lex_studies.py --ollama --chapters …` (see script docstring; set `LEX_STUDIES_MODEL` as needed).

See `SOURCES.txt` for licenses and URLs.
