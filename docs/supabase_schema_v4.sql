-- Phase 4: monitored accounts (one-time avatar/profile + per-account watermark)
-- and a run "kind" so profile-fetch runs are separate from post collection.

create table if not exists public.monitored_accounts (
  source_id text not null references public.data_sources(id) on delete cascade,
  handle text not null,
  author_name text,
  avatar_url text,
  bio text,
  profile_url text,
  last_post_at timestamptz,          -- watermark: newest collected post time for this account
  onboarded_at timestamptz,          -- when the avatar/profile was fetched (one-time)
  created_at timestamptz not null default now(),
  primary key (source_id, handle)
);

alter table public.monitored_accounts enable row level security;

-- 'collect' = post collection (no avatars); 'profile' = one-time avatar/profile fetch.
alter table public.data_source_runs
  add column if not exists kind text not null default 'collect';

create index if not exists monitored_accounts_source_handle_idx
  on public.monitored_accounts (source_id, handle);
