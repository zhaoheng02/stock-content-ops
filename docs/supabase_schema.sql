create table if not exists public.data_sources (
  id text primary key,
  name text not null,
  platform text not null,
  cadence_minutes integer not null default 30 check (cadence_minutes >= 5),
  targets jsonb not null default '[]'::jsonb,
  min_score integer not null default 70 check (min_score between 0 and 100),
  material_strategy text not null default 'download_media',
  credential_key text not null default 'X_BEARER_TOKEN',
  credential_file text not null default '/Users/bytedance/personal.config',
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.data_source_runs (
  id text primary key,
  source_id text not null references public.data_sources(id) on delete cascade,
  started_at timestamptz not null,
  finished_at timestamptz not null,
  status text not null check (status in ('success', 'failed')),
  items_collected integer not null default 0,
  output_path text not null default '',
  message text not null default ''
);

create index if not exists data_source_runs_source_started_idx
  on public.data_source_runs (source_id, started_at desc);

-- Raw collected posts (X / Twitter and future platforms).
-- Stores the full captured content so the data source page and lead pool
-- can show everything that was collected in a run.
create table if not exists public.source_posts (
  content_hash text primary key,
  source_id text references public.data_sources(id) on delete set null,
  run_id text references public.data_source_runs(id) on delete set null,
  platform text not null default 'x',
  post_id text,
  author_handle text not null,
  author_name text,
  author_avatar_url text,
  author_bio text,
  text text not null default '',
  url text,
  published_at timestamptz,
  published_at_raw text,
  image_urls jsonb not null default '[]'::jsonb,
  video_urls jsonb not null default '[]'::jsonb,
  link_cards jsonb not null default '[]'::jsonb,
  quote jsonb,
  metrics jsonb not null default '{}'::jsonb,
  media_error text,
  collected_at timestamptz not null default now(),
  first_seen_at timestamptz not null default now(),
  raw jsonb
);

create index if not exists source_posts_author_published_idx
  on public.source_posts (author_handle, published_at desc);

create index if not exists source_posts_run_idx
  on public.source_posts (run_id);

create unique index if not exists source_posts_platform_postid_idx
  on public.source_posts (platform, post_id) where post_id is not null;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists data_sources_set_updated_at on public.data_sources;
create trigger data_sources_set_updated_at
before update on public.data_sources
for each row execute function public.set_updated_at();
