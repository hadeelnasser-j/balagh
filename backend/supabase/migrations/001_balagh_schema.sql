-- BALAGH backend schema for Supabase (Postgres).
-- Run in the Supabase SQL editor or with `supabase db push`.
-- The backend uses the service-role key, so RLS is enabled with no public policies.

create extension if not exists "pgcrypto";

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  source_language text not null default 'ar',
  target_language text not null default 'en',
  dubbing_mode text not null default 'timed' check (dubbing_mode in ('faithful','timed','simplified')),
  status text not null default 'created',
  original_filename text,
  video_storage_path text,
  audio_storage_path text,
  srt_storage_path text,
  srt_mode text,
  dubbed_audio_path text,
  dubbed_video_path text,
  duration_seconds double precision,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.processing_jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  job_type text not null check (job_type in ('upload','transcription','translation','dubbing','rendering')),
  status text not null default 'queued',
  progress integer not null default 0 check (progress between 0 and 100),
  current_step text,
  error_message text,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists processing_jobs_project_idx on public.processing_jobs(project_id, created_at desc);

create table if not exists public.video_segments (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  segment_index integer not null,
  start_time double precision not null,
  end_time double precision not null,
  original_text text not null,
  translated_text text,
  edited_translation text,
  final_translation text,
  translation_status text not null default 'pending' check (translation_status in ('pending','translating','translated','failed')),
  translation_warning text,
  translation_error text,
  review_status text not null default 'pending' check (review_status in ('pending','edited','approved','rejected')),
  review_note text,
  needs_human_review boolean not null default true,
  source_language text,
  target_language text not null default 'en',
  content_type text not null default 'general' check (content_type in ('quran','hadith','general','uncertain')),
  source_verification_status text not null default 'pending',
  source_review_status text not null default 'pending',
  source_match_score double precision,
  reference text,
  verification_source text,
  translation_source text,
  translation_origin text,
  hadith_grade text,
  source_text text,
  source_url text,
  source_id text,
  quran_suspected boolean not null default false,
  detection_reason text,
  meaning_lock_status text not null default 'none',
  text_verified boolean not null default false,
  translation_verified boolean not null default false,
  recitation_verified boolean not null default false,
  ready_for_dubbing boolean not null default false,
  dubbed_audio_path text,
  audio_duration double precision,
  timing_status text,
  tempo_factor double precision,
  audio_review_status text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, segment_index)
);
create index if not exists video_segments_project_idx on public.video_segments(project_id, segment_index);

-- Hard guarantee at the database level: Quran segments can never carry TTS audio.
alter table public.video_segments drop constraint if exists quran_never_dubbed;
alter table public.video_segments add constraint quran_never_dubbed
  check (content_type <> 'quran' or dubbed_audio_path is null);

create table if not exists public.source_matches (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  segment_id uuid not null references public.video_segments(id) on delete cascade,
  source_id text not null,
  source_type text not null check (source_type in ('quran','hadith')),
  source_name text,
  title text,
  reference_key text,
  exact_quote text,
  translation text,
  translation_source text,
  hadith_grade text,
  url text,
  match_type text not null,
  match_score double precision not null,
  status text not null default 'candidate' check (status in ('candidate','verified','rejected','conflict')),
  reviewed_by text,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists source_matches_segment_idx on public.source_matches(segment_id);

create table if not exists public.translation_reviews (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  segment_id uuid not null references public.video_segments(id) on delete cascade,
  action text not null check (action in ('edit','approve','reject','retranslate','content_type_change')),
  previous_translation text,
  new_translation text,
  note text,
  reviewed_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.audio_reviews (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  segment_id uuid not null references public.video_segments(id) on delete cascade,
  action text not null check (action in ('generated','approve','reject')),
  audio_path text,
  audio_duration double precision,
  reviewed_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.dubbed_outputs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  job_id uuid references public.processing_jobs(id) on delete set null,
  video_path text not null,
  audio_path text not null,
  synthesized_segments integer not null default 0,
  original_audio_segments integer not null default 0,
  duration_seconds double precision,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.meaning_locks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  segment_id uuid not null references public.video_segments(id) on delete cascade,
  original_span text not null,
  translated_span text,
  expected_terms text,
  lock_type text not null,
  risk_level text not null check (risk_level in ('low','medium','high')),
  review_status text not null default 'pending' check (review_status in ('pending','approved','rejected')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.recovered_sources (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  segment_id uuid references public.video_segments(id) on delete cascade,
  type text not null check (type in ('quran','hadith')),
  source text not null,
  source_id text not null,
  reference text,
  section text,
  confidence double precision not null,
  full_text text not null,
  translation text,
  status text not null default 'candidate' check (status in ('recovered','candidate','approved','rejected')),
  reviewed_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

do $$
declare t text;
begin
  foreach t in array array['projects','processing_jobs','video_segments','source_matches','translation_reviews',
                           'audio_reviews','dubbed_outputs','meaning_locks','recovered_sources']
  loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

-- Storage buckets (private). Only used when SUPABASE_STORAGE_ENABLED=true.
insert into storage.buckets (id, name, public) values
  ('videos','videos',false), ('audio','audio',false),
  ('subtitles','subtitles',false), ('dubbed-outputs','dubbed-outputs',false)
on conflict (id) do nothing;
