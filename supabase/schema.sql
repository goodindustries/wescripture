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

create policy "profiles_public_read"
  on public.profiles
  for select
  using (true);

create policy "profiles_write_own"
  on public.profiles
  for insert
  with check (auth.uid() = id);

create policy "profiles_update_own"
  on public.profiles
  for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

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

create policy "friendships_public_read"
  on public.friendships
  for select
  using (true);

create policy "friendships_write_own"
  on public.friendships
  for insert
  with check (auth.uid() = user_id);

create policy "friendships_update_own"
  on public.friendships
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "friendships_delete_own"
  on public.friendships
  for delete
  using (auth.uid() = user_id);

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

create policy "verse_annotations_public_read"
  on public.verse_annotations
  for select
  using (true);

create policy "verse_annotations_write_own"
  on public.verse_annotations
  for insert
  with check (auth.uid() = user_id);

create policy "verse_annotations_update_own"
  on public.verse_annotations
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "verse_annotations_delete_own"
  on public.verse_annotations
  for delete
  using (auth.uid() = user_id);

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

create policy "morsels_public_read"
  on public.morsels
  for select
  using (true);

create policy "morsels_write_own"
  on public.morsels
  for insert
  with check (auth.uid() = user_id);

create policy "morsels_update_own"
  on public.morsels
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "morsels_delete_own"
  on public.morsels
  for delete
  using (auth.uid() = user_id);

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

create policy "activity_events_public_read"
  on public.activity_events
  for select
  using (true);

create policy "activity_events_write_own"
  on public.activity_events
  for insert
  with check (auth.uid() = actor_id);

-- Convenience view for feeds (join handle)
create or replace view public.activity_feed as
select
  e.*,
  p.handle,
  p.display_name
from public.activity_events e
left join public.profiles p on p.id = e.actor_id;

