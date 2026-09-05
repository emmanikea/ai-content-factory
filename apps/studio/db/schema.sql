-- AI Content Factory V2 schema
-- Portable Postgres; works with Supabase, Neon, or standard Postgres.

create extension if not exists pgcrypto;

create table if not exists characters (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  kind text not null check (kind in ('real_person','synthetic','brand_mascot')),
  description text,
  voice_profile_id text,
  consent_status text not null default 'not_required' check (consent_status in ('not_required','pending','verified','revoked')),
  consent_notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists references (
  id uuid primary key default gen_random_uuid(),
  character_id uuid references characters(id) on delete cascade,
  kind text not null check (kind in ('image','video','audio','performance','location','wardrobe')),
  storage_key text not null,
  source_url text,
  label text,
  consent_verified boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  project_type text not null default 'social_video',
  status text not null default 'active',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists generation_jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete set null,
  character_id uuid references characters(id) on delete set null,
  provider text not null,
  provider_job_id text,
  model text,
  tier text not null default 'standard',
  status text not null default 'queued' check (status in ('queued','running','completed','failed','cancelled','expired')),
  prompt text not null,
  request_json jsonb not null default '{}'::jsonb,
  response_json jsonb not null default '{}'::jsonb,
  attempt_number integer not null default 1,
  duration_seconds numeric,
  resolution text,
  aspect_ratio text,
  estimated_cost_usd numeric(12,6),
  actual_cost_usd numeric(12,6),
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists generation_jobs_status_idx on generation_jobs(status, created_at desc);
create index if not exists generation_jobs_project_idx on generation_jobs(project_id, created_at desc);
create index if not exists generation_jobs_character_idx on generation_jobs(character_id, created_at desc);

create table if not exists assets (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete set null,
  generation_job_id uuid references generation_jobs(id) on delete set null,
  character_id uuid references characters(id) on delete set null,
  kind text not null check (kind in ('image','video','audio','thumbnail','caption','other')),
  storage_key text not null,
  source_url text,
  mime_type text,
  width integer,
  height integer,
  duration_seconds numeric,
  provenance jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists quality_reviews (
  id uuid primary key default gen_random_uuid(),
  generation_job_id uuid not null references generation_jobs(id) on delete cascade,
  reviewer text not null,
  identity_score numeric,
  motion_score numeric,
  prompt_score numeric,
  artifact_score numeric,
  lip_sync_score numeric,
  overall_score numeric,
  passed boolean,
  notes text,
  raw_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists approval_events (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  asset_id uuid references assets(id) on delete cascade,
  decision text not null check (decision in ('approved','rejected','needs_changes')),
  notes text,
  actor text,
  created_at timestamptz not null default now()
);

create table if not exists cost_events (
  id uuid primary key default gen_random_uuid(),
  generation_job_id uuid references generation_jobs(id) on delete cascade,
  provider text not null,
  model text,
  amount_usd numeric(12,6) not null,
  units numeric,
  unit_type text,
  source text not null default 'estimated' check (source in ('estimated','provider','reconciled')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create or replace function set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists characters_set_updated_at on characters;
create trigger characters_set_updated_at before update on characters for each row execute function set_updated_at();

drop trigger if exists projects_set_updated_at on projects;
create trigger projects_set_updated_at before update on projects for each row execute function set_updated_at();

drop trigger if exists generation_jobs_set_updated_at on generation_jobs;
create trigger generation_jobs_set_updated_at before update on generation_jobs for each row execute function set_updated_at();
