# server/migrations/ — retired

Historical home of the pre-Supabase-auth schema (`001_init.sql`: local `users`,
`sessions`, `password_hash`). Retired 2026-04-19 as part of the rearchitect
(ledger task T-0027 under plan `wescripture-rearchitect-reset`).

## Canonical migration home

All Postgres schema changes now live under [`supabase/`](../../supabase/):

- [`supabase/schema.sql`](../../supabase/schema.sql) — social + corpus v0
  (profiles, annotations, morsels, highlights, activity, monitor samples,
  legacy corpus_* tables). Treat as implicit migration `001`.
- [`supabase/migrations/002_corpus_schema.sql`](../../supabase/migrations/002_corpus_schema.sql)
  — canonical corpus tables for v1: `volume`, `book`, `chapter`, `verse`,
  `verse_variant`, `commentary_source`, `commentary_para`, `embedding`
  (pgvector 384), `connection`.

## Lineage

```
001  supabase/schema.sql              social + corpus v0 (legacy corpus_* kept for rollback)
002  supabase/migrations/002_*.sql    rearchitect corpus tables (this rewrite)
```

Future migrations: add `003_*.sql` onward under `supabase/migrations/`. Do not
add new files under `server/migrations/` — it stays empty as a historical marker.
