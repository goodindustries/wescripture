-- 002_corpus_schema.sql — WeScripture canonical corpus tables (rearchitect v1).
--
-- Introduces the authoritative schema for:
--   volume / book / chapter / verse        -- standard works hierarchy
--   verse_variant                           -- JST + footnotes + translator notes
--   commentary_source / commentary_para     -- Donaldson + future commentary sets
--   embedding                               -- pgvector(384) over verse + commentary_para
--   connection                              -- directed similarity edges, top-K + cosine
--
-- Row-level security model: public read on all corpus tables; writes via
-- service role only (service role bypasses RLS). Per-row ownership is not a
-- concept for canonical corpus data.
--
-- Apply via Supabase SQL editor or `supabase db push`. Idempotent on extensions
-- and table creation; re-running is safe.

create extension if not exists "pgcrypto";
create extension if not exists "vector";
