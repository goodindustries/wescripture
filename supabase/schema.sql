-- Supabase schema for WeScripture social persistence (phase 0: public read, authenticated write-own).
-- Apply in Supabase SQL editor.

-- Extensions
create extension if not exists "pgcrypto";

-- ── Profiles ────────────────────────────────────────────────────────────────
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  handle text not null unique,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

do $$ begin
  create policy "profiles_public_read"
    on public.profiles
    for select
    using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "profiles_write_own"
    on public.profiles
    for insert
    with check (auth.uid() = id);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "profiles_update_own"
    on public.profiles
    for update
    using (auth.uid() = id)
    with check (auth.uid() = id);
exception when duplicate_object then null; end $$;

-- ── Friendships (phase 0: public read; unilateral follow allowed) ───────────
create table if not exists public.friendships (
  user_id uuid not null references auth.users(id) on delete cascade,
  friend_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'accepted',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, friend_id),
  constraint friendships_not_self check (user_id <> friend_id)
);

alter table public.friendships enable row level security;

do $$ begin
  create policy "friendships_public_read"
    on public.friendships
    for select
    using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "friendships_write_own"
    on public.friendships
    for insert
    with check (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "friendships_update_own"
    on public.friendships
    for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "friendships_delete_own"
    on public.friendships
    for delete
    using (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

-- ── Verse annotations ───────────────────────────────────────────────────────
create table if not exists public.verse_annotations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  verse_ref text not null,
  body text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists verse_annotations_ref_idx on public.verse_annotations (verse_ref);
create index if not exists verse_annotations_user_ref_idx on public.verse_annotations (user_id, verse_ref);

alter table public.verse_annotations enable row level security;

do $$ begin
  create policy "verse_annotations_public_read"
    on public.verse_annotations
    for select
    using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "verse_annotations_write_own"
    on public.verse_annotations
    for insert
    with check (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "verse_annotations_update_own"
    on public.verse_annotations
    for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "verse_annotations_delete_own"
    on public.verse_annotations
    for delete
    using (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

-- ── Morsels (save anything) ────────────────────────────────────────────────
create table if not exists public.morsels (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  kind text not null default 'note',
  payload jsonb not null default '{}'::jsonb,
  verse_ref text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists morsels_user_created_idx on public.morsels (user_id, created_at desc);
create index if not exists morsels_verse_ref_idx on public.morsels (verse_ref);

alter table public.morsels enable row level security;

do $$ begin
  create policy "morsels_public_read"
    on public.morsels
    for select
    using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "morsels_write_own"
    on public.morsels
    for insert
    with check (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "morsels_update_own"
    on public.morsels
    for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "morsels_delete_own"
    on public.morsels
    for delete
    using (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

-- ── Highlights (per-user) ───────────────────────────────────────────────────
-- User-owned highlights across any target type (verse, text range, entity, morsel, etc.).

create table if not exists public.highlights (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  target_type text not null,
  target_id text not null,
  color_key text not null default 'temple_granite',
  note text not null default '',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint highlights_target_chk check (length(target_type) > 0 and length(target_id) > 0)
);

create unique index if not exists highlights_user_target_uniq on public.highlights (user_id, target_type, target_id);
create index if not exists highlights_user_updated_idx on public.highlights (user_id, updated_at desc);
create index if not exists highlights_target_idx on public.highlights (target_type, target_id);

alter table public.highlights enable row level security;

do $$ begin
  create policy "highlights_public_read"
    on public.highlights
    for select
    using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "highlights_write_own"
    on public.highlights
    for insert
    with check (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "highlights_update_own"
    on public.highlights
    for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "highlights_delete_own"
    on public.highlights
    for delete
    using (auth.uid() = user_id);
exception when duplicate_object then null; end $$;

-- ── Activity events (public history/feed) ──────────────────────────────────
create table if not exists public.activity_events (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid not null references auth.users(id) on delete cascade,
  type text not null,
  verse_ref text,
  object_table text,
  object_id uuid,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists activity_events_created_idx on public.activity_events (created_at desc);
create index if not exists activity_events_actor_created_idx on public.activity_events (actor_id, created_at desc);
create index if not exists activity_events_verse_ref_idx on public.activity_events (verse_ref);

alter table public.activity_events enable row level security;

do $$ begin
  create policy "activity_events_public_read"
    on public.activity_events
    for select
    using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "activity_events_write_own"
    on public.activity_events
    for insert
    with check (auth.uid() = actor_id);
exception when duplicate_object then null; end $$;

-- Convenience view for feeds (join handle)
create or replace view public.activity_feed as
select
  e.*,
  p.handle,
  p.display_name
from public.activity_events e
left join public.profiles p on p.id = e.actor_id;

-- ── Monitor samples (shared metrics history) ───────────────────────────────
-- Public read; service-role writes (service role bypasses RLS).

create table if not exists public.monitor_samples (
  ts timestamptz primary key,
  links bigint not null,
  paragraphs bigint not null,
  sources bigint not null,
  verses_with_any bigint not null default 0,
  linked_docs bigint not null default 0,
  linked_paragraphs bigint not null default 0,
  created_at timestamptz not null default now()
);

alter table public.monitor_samples enable row level security;

do $$ begin
  create policy "monitor_samples_public_read"
    on public.monitor_samples
    for select
    using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "monitor_samples_no_write"
    on public.monitor_samples
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

-- ── Corpus (Supabase source-of-truth) ───────────────────────────────────────
-- Public read, service-role-only writes (service role bypasses RLS).

create table if not exists public.corpus_collections (
  id text primary key,
  label text not null,
  description text not null default '',
  sort int not null default 1000,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.corpus_collections enable row level security;
do $$ begin
  create policy "corpus_collections_public_read"
    on public.corpus_collections
    for select
    using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "corpus_collections_no_write"
    on public.corpus_collections
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

create table if not exists public.corpus_sources (
  id text primary key,
  collection_id text references public.corpus_collections(id) on delete set null,
  title text not null,
  author text not null default '',
  year int,
  canonical_url text not null default '',
  license_type text not null default 'unknown',
  license_url text,
  redistributable bool not null default false,
  ingest_mode text not null default 'ingest',
  group_id text,
  group_label text,
  group_meta text,
  source_meta text,
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  constraint corpus_sources_ingest_mode_chk check (ingest_mode in ('ingest','link_only'))
);

create index if not exists corpus_sources_collection_idx on public.corpus_sources (collection_id, year desc nulls last);
create index if not exists corpus_sources_group_idx on public.corpus_sources (collection_id, group_id);

alter table public.corpus_sources enable row level security;
do $$ begin
  create policy "corpus_sources_public_read"
    on public.corpus_sources
    for select
    using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "corpus_sources_no_write"
    on public.corpus_sources
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

create table if not exists public.corpus_paragraphs (
  source_id text not null references public.corpus_sources(id) on delete cascade,
  para_idx int not null,
  text text not null,
  text_hash text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (source_id, para_idx),
  constraint corpus_paragraphs_para_idx_chk check (para_idx >= 1)
);

create index if not exists corpus_paragraphs_source_idx on public.corpus_paragraphs (source_id, para_idx);

alter table public.corpus_paragraphs enable row level security;
do $$ begin
  create policy "corpus_paragraphs_public_read"
    on public.corpus_paragraphs
    for select
    using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "corpus_paragraphs_no_write"
    on public.corpus_paragraphs
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

create table if not exists public.corpus_verse_catalog (
  verse_key text primary key,
  book text not null,
  chapter int not null,
  verse int not null,
  text text not null,
  volume text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists corpus_verse_catalog_book_idx on public.corpus_verse_catalog (book, chapter, verse);

alter table public.corpus_verse_catalog enable row level security;
do $$ begin
  create policy "corpus_verse_catalog_public_read"
    on public.corpus_verse_catalog
    for select
    using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "corpus_verse_catalog_no_write"
    on public.corpus_verse_catalog
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

create table if not exists public.corpus_correlations (
  verse_key text not null references public.corpus_verse_catalog(verse_key) on delete cascade,
  engine text not null default 'sentence_transformers',
  matches_json jsonb not null default '[]'::jsonb,
  generated_at timestamptz not null default now(),
  primary key (verse_key, engine)
);

alter table public.corpus_correlations enable row level security;
do $$ begin
  create policy "corpus_correlations_public_read"
    on public.corpus_correlations
    for select
    using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "corpus_correlations_no_write"
    on public.corpus_correlations
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

create table if not exists public.corpus_chapter_graphs (
  chapter_id text primary key,
  graph jsonb not null,
  generated_at timestamptz not null default now()
);

alter table public.corpus_chapter_graphs enable row level security;
do $$ begin
  create policy "corpus_chapter_graphs_public_read"
    on public.corpus_chapter_graphs
    for select
    using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "corpus_chapter_graphs_no_write"
    on public.corpus_chapter_graphs
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

create table if not exists public.corpus_source_links (
  source_id text not null references public.corpus_sources(id) on delete cascade,
  para_idx int not null,
  refs jsonb not null default '[]'::jsonb,
  primary key (source_id, para_idx)
);

alter table public.corpus_source_links enable row level security;
do $$ begin
  create policy "corpus_source_links_public_read"
    on public.corpus_source_links
    for select
    using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "corpus_source_links_no_write"
    on public.corpus_source_links
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

create table if not exists public.corpus_source_citations (
  source_id text not null references public.corpus_sources(id) on delete cascade,
  para_idx int not null,
  refs jsonb not null default '[]'::jsonb,
  primary key (source_id, para_idx)
);

alter table public.corpus_source_citations enable row level security;
do $$ begin
  create policy "corpus_source_citations_public_read"
    on public.corpus_source_citations
    for select
    using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "corpus_source_citations_no_write"
    on public.corpus_source_citations
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

-- ── Corpus backlog (what still needs work) ──────────────────────────────────
-- Intended for /monitor: what to ingest, encode, correlate, etc.

create table if not exists public.corpus_backlog (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  author text not null default '',
  canonical_url text not null default '',
  license text not null default '',
  status text not null default 'todo',
  priority int not null default 0,
  needs jsonb not null default '{"pull":true,"encode":true,"correlate":true}'::jsonb,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint corpus_backlog_status_chk check (status in ('todo','doing','blocked','done'))
);

create index if not exists corpus_backlog_status_priority_idx on public.corpus_backlog (status, priority desc, updated_at desc);

alter table public.corpus_backlog enable row level security;
do $$ begin
  create policy "corpus_backlog_public_read"
    on public.corpus_backlog
    for select
    using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "corpus_backlog_no_write"
    on public.corpus_backlog
    for all
    using (false)
    with check (false);
exception when duplicate_object then null; end $$;

