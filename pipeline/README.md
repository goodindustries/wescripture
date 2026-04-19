# pipeline/

Corpus ingestion DAG for WeScripture (v1 rearchitect).

Owns the path from raw canonical sources → normalized text → JST-woven verses →
Donaldson commentary → Supabase `verse` / `verse_variant` / `commentary_para` →
embeddings → cross-text `connection` edges.

## Entry point

```
make all
```

See `Makefile` for the DAG. Each target is a pure function over the previous
stage's artifacts under `build/`.

## Stages

| Target     | Purpose                                                               |
| ---------- | --------------------------------------------------------------------- |
| `fetch`    | Download raw canonical sources (OpenScriptures, BoMC, etc.)           |
| `normalize`| Clean HTML/XML → canonical verse JSON keyed by `{book}.{ch}.{v}`      |
| `jst_weave`| Merge JST variants inline as `verse_variant` rows                     |
| `donaldson`| Ingest Donaldson commentary paragraphs, map to verse ranges           |
| `upsert`   | Push normalized rows into Supabase via service-role                   |
| `embed`    | Compute verse + commentary embeddings, store in pgvector              |
| `connect`  | Build `connection` table (top-K=40, cosine >= 0.28)                   |
| `audit`    | Strict audit: row counts, orphan checks, license provenance           |

## Layout

```
pipeline/
  Makefile              # DAG
  requirements.txt      # pinned deps
  fetch/                # source-specific fetchers
  normalize/            # HTML/XML → verse JSON
  weave/                # JST merger
  donaldson/            # commentary ingestor
  db/                   # Supabase upsert helpers
  embed/                # embedding + pgvector writer
  connect/              # similarity / connection builder
  audit/                # strict audit checks
  build/                # artifacts (gitignored)
  tests/                # pytest — invariants per stage
```

## Provenance

Every row upserted carries `source_slug` and `license` — see
`CORPUS_SOURCES.md` (tracked by ledger task T-0001).
