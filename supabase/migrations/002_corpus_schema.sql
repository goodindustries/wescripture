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

-- ── chapter ────────────────────────────────────────────────────────────────
-- Composite PK (book_slug, number). Canonical id: {book_slug}.{number}
-- (e.g. gen.1). A surrogate uuid is also exposed for FK targets that prefer
-- a single column.
create table if not exists public.chapter (
  id          uuid primary key default gen_random_uuid(),
  book_slug   text not null references public.book(slug) on delete cascade,
  number      int  not null,
  verse_count int  not null default 0,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (book_slug, number),
  constraint chapter_number_chk check (number >= 1)
);

create index if not exists chapter_book_num_idx on public.chapter (book_slug, number);

alter table public.chapter enable row level security;
do $$ begin
  create policy "chapter_public_read" on public.chapter for select using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "chapter_no_write" on public.chapter for all using (false) with check (false);
exception when duplicate_object then null; end $$;

-- ── verse ──────────────────────────────────────────────────────────────────
-- Composite PK (book_slug, chapter_number, verse_number). Canonical id:
-- {volume_slug}.{book_slug}.{chapter_number}.{verse_number} is materialized
-- as `ref` for external consumers; internal FKs use surrogate uuid.
create table if not exists public.verse (
  id             uuid primary key default gen_random_uuid(),
  book_slug      text not null references public.book(slug) on delete cascade,
  chapter_number int  not null,
  verse_number   int  not null,
  ref            text not null unique,
  text           text not null,
  source_slug    text not null default '',
  license        text not null default '',
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (book_slug, chapter_number, verse_number),
  constraint verse_chapter_chk check (chapter_number >= 1),
  constraint verse_number_chk  check (verse_number >= 1),
  constraint verse_ref_format_chk check (ref ~ '^[a-z0-9_]+\.[a-z0-9_]+\.[0-9]+\.[0-9]+$')
);

create index if not exists verse_chapter_idx on public.verse (book_slug, chapter_number, verse_number);

alter table public.verse enable row level security;
do $$ begin
  create policy "verse_public_read" on public.verse for select using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "verse_no_write" on public.verse for all using (false) with check (false);
exception when duplicate_object then null; end $$;
