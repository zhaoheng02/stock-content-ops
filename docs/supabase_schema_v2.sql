-- Phase 2 schema: drafts, publish accounts, assets, team, proxies, metrics.
-- Run in Supabase SQL Editor after docs/supabase_schema.sql.

-- Generated platform drafts. Drives the Studio output, Review queue, and
-- Publish records/queue/retry views. One row per (post, platform) version.
create table if not exists public.drafts (
  id text primary key,
  post_id text,
  source_id text,
  platform text not null,                 -- xiaohongshu | wechat_article | video_account | douyin_script
  title text not null default '',
  body text not null default '',
  tags jsonb not null default '[]'::jsonb,
  status text not null default 'needs_review'
    check (status in ('draft','needs_review','approved','rejected','scheduled','published','failed')),
  owner text not null default '内容组',
  account_id text,
  ai_analysis text not null default '',
  source_url text not null default '',
  scheduled_at timestamptz,
  published_at timestamptz,
  publish_error text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists drafts_status_idx on public.drafts (status, updated_at desc);
create index if not exists drafts_platform_idx on public.drafts (platform);

-- Publishing accounts (国内发布平台授权).
create table if not exists public.publish_accounts (
  id text primary key,
  platform text not null,                 -- 小红书 | 公众号 | 视频号 | 抖音 | ...
  slug text not null default '',
  name text not null,
  status text not null default '未授权'
    check (status in ('已授权','待登录','未授权')),
  mode text not null default '浏览器发布',
  proxy text not null default '默认',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Asset library (下载后的素材).
create table if not exists public.assets (
  id text primary key,
  name text not null,
  type text not null default '图片',       -- 图片 | 视频 | 文章
  size_bytes bigint not null default 0,
  group_name text not null default '未分组',
  used text not null default '',
  url text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists assets_group_idx on public.assets (group_name);

-- Team members and roles.
create table if not exists public.team_members (
  id text primary key,
  name text not null,
  role text not null default '编辑',
  account_count integer not null default 0,
  status text not null default '在线'
    check (status in ('在线','运行中','离线')),
  joined_at date not null default current_date,
  created_at timestamptz not null default now()
);

-- Publishing proxies (出海发布网络环境).
create table if not exists public.proxies (
  id text primary key,
  name text not null,
  type text not null default 'HTTP'
    check (type in ('HTTP','SOCKS5')),
  host text not null default '',
  port integer not null default 0,
  username text not null default '',
  password text not null default '',
  status text not null default '正常',
  created_at timestamptz not null default now()
);

-- Per-publish performance metrics, aggregated by the Analytics page.
create table if not exists public.publish_metrics (
  id text primary key,
  draft_id text references public.drafts(id) on delete cascade,
  platform text not null default '',
  account_id text,
  views integer not null default 0,
  likes integer not null default 0,
  comments integer not null default 0,
  shares integer not null default 0,
  leads integer not null default 0,
  recorded_at timestamptz not null default now()
);

create index if not exists publish_metrics_recorded_idx on public.publish_metrics (recorded_at desc);

drop trigger if exists drafts_set_updated_at on public.drafts;
create trigger drafts_set_updated_at
before update on public.drafts
for each row execute function public.set_updated_at();

drop trigger if exists publish_accounts_set_updated_at on public.publish_accounts;
create trigger publish_accounts_set_updated_at
before update on public.publish_accounts
for each row execute function public.set_updated_at();
