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

-- ── verse_variant ──────────────────────────────────────────────────────────
-- Variant renderings attached to a base verse: JST, footnotes, translator
-- notes. The enum is a CHECK constraint (not a pg ENUM type) to keep schema
-- evolution cheap — add new kinds with an ALTER TABLE, no ALTER TYPE.
create table if not exists public.verse_variant (
  id           uuid primary key default gen_random_uuid(),
  verse_id     uuid not null references public.verse(id) on delete cascade,
  variant_kind text not null,
  text         text not null,
  label        text not null default '',
  source_slug  text not null default '',
  license      text not null default '',
  sort         int  not null default 0,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  constraint verse_variant_kind_chk
    check (variant_kind in ('jst', 'footnote', 'translator_note'))
);

create index if not exists verse_variant_verse_idx on public.verse_variant (verse_id, variant_kind, sort);

alter table public.verse_variant enable row level security;
do $$ begin
  create policy "verse_variant_public_read" on public.verse_variant for select using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "verse_variant_no_write" on public.verse_variant for all using (false) with check (false);
exception when duplicate_object then null; end $$;

-- ── commentary_source ──────────────────────────────────────────────────────
-- One row per commentary work (e.g. 'donaldson', future 'jfb', 'clarke').
-- Carries license + provenance so readers can attribute per paragraph.
create table if not exists public.commentary_source (
  slug         text primary key,
  label        text not null,
  author       text not null default '',
  year         int,
  canonical_url text not null default '',
  license      text not null default 'unknown',
  license_url  text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  constraint commentary_source_slug_chk check (slug = lower(slug) and length(slug) between 2 and 32)
);

alter table public.commentary_source enable row level security;
do $$ begin
  create policy "commentary_source_public_read" on public.commentary_source for select using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "commentary_source_no_write" on public.commentary_source for all using (false) with check (false);
exception when duplicate_object then null; end $$;

-- ── commentary_para ────────────────────────────────────────────────────────
-- Paragraph of commentary, mapped to an inclusive verse range
-- (verse_start_id .. verse_end_id). Ranges that span chapters are legal and
-- enforced only at ingest time; schema does not require same-chapter.
-- A commentary paragraph may attach to a single verse by setting
-- verse_end_id = verse_start_id.
create table if not exists public.commentary_para (
  id              uuid primary key default gen_random_uuid(),
  source_slug     text not null references public.commentary_source(slug) on delete cascade,
  verse_start_id  uuid not null references public.verse(id) on delete cascade,
  verse_end_id    uuid not null references public.verse(id) on delete cascade,
  para_idx        int  not null,
  text            text not null,
  text_hash       text not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (source_slug, para_idx),
  constraint commentary_para_idx_chk check (para_idx >= 1)
);

create index if not exists commentary_para_start_idx on public.commentary_para (verse_start_id);
create index if not exists commentary_para_source_idx on public.commentary_para (source_slug, para_idx);

alter table public.commentary_para enable row level security;
do $$ begin
  create policy "commentary_para_public_read" on public.commentary_para for select using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "commentary_para_no_write" on public.commentary_para for all using (false) with check (false);
exception when duplicate_object then null; end $$;
