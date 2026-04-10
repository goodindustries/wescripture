# Corpus source HTML — paragraph contract

Source documents under `library/` (paths listed in `source_toc.json` / `sourceMeta`) must keep **stable paragraph indices** for `source_links.json` and reader deep-links.

## Rules

1. One logical paragraph = one `<p class="source-para">` (or the markup your ingest uses consistently).
2. Do not nest block elements inside a single indexed `<p>` in ways that change para count when re-saving.
3. Normalize whitespace in a dedicated cleanup pass; avoid manual duplication of OCR line breaks inside one `<p>`.

## Lint

```bash
python3 lds_pipeline/lint_source_paras.py
python3 lds_pipeline/lint_source_paras.py --max-files 20
```

Reports files with zero `source-para` paragraphs or suspiciously short documents.
