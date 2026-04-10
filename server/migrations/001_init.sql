-- Initial schema: user identity + durable study data.

create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  password_hash text,
  created_at timestamptz not null default now()
);

create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  token_hash text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz
);

create table if not exists profiles (
  user_id uuid primary key references users(id) on delete cascade,
  display_name text,
  prefs_json jsonb not null default '{}'::jsonb
);

-- Content references are stored as opaque strings for now (e.g. "John 3:16", "bom:alma:32:1-5").
create table if not exists reading_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  content_ref text not null,
  last_position text,
  updated_at timestamptz not null default now(),
  unique (user_id, content_ref)
);

create table if not exists saved_passages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  content_ref text not null,
  label text,
  created_at timestamptz not null default now()
);

create table if not exists notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  content_ref text not null,
  body text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists highlights (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  content_ref text not null,
  range_json jsonb not null,
  color text,
  created_at timestamptz not null default now()
);

create index if not exists idx_sessions_user_id on sessions(user_id);
create index if not exists idx_reading_history_user_id on reading_history(user_id);
create index if not exists idx_saved_passages_user_id on saved_passages(user_id);
create index if not exists idx_notes_user_id on notes(user_id);
create index if not exists idx_highlights_user_id on highlights(user_id);

