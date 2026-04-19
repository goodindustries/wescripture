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

-- ── volume ─────────────────────────────────────────────────────────────────
-- The 5 standard-works volumes (ot, nt, bom, dc, pgp). Slug is stable PK and
-- appears as the first segment of every canonical id (e.g. ot.gen.1.1).
create table if not exists public.volume (
  slug       text primary key,
  label      text not null,
  sort       int  not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint volume_slug_chk check (slug = lower(slug) and length(slug) between 2 and 16)
);

alter table public.volume enable row level security;
do $$ begin
  create policy "volume_public_read" on public.volume for select using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "volume_no_write" on public.volume for all using (false) with check (false);
exception when duplicate_object then null; end $$;

-- ── book ───────────────────────────────────────────────────────────────────
-- All 67 books across the five volumes. Slug is stable PK and appears as the
-- second segment of every canonical id (e.g. ot.gen.1.1 -> book.slug='gen').
create table if not exists public.book (
  slug        text primary key,
  volume_slug text not null references public.volume(slug) on delete restrict,
  label       text not null,
  short_label text not null,
  sort        int  not null,
  chapter_count int not null default 0,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint book_slug_chk check (slug = lower(slug) and length(slug) between 2 and 32),
  constraint book_sort_chk check (sort >= 0)
);

create index if not exists book_volume_sort_idx on public.book (volume_slug, sort);

alter table public.book enable row level security;
do $$ begin
  create policy "book_public_read" on public.book for select using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "book_no_write" on public.book for all using (false) with check (false);
exception when duplicate_object then null; end $$;
