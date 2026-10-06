-- Run in the Supabase SQL editor to verify the BALAGH schema, RLS and the Quran constraint.
-- Every row should show ok = true.
with expected(tbl) as (values
  ('projects'),('processing_jobs'),('video_segments'),('source_matches'),('translation_reviews'),
  ('audio_reviews'),('dubbed_outputs'),('meaning_locks'),('recovered_sources'))
select 'table ' || e.tbl as check_name,
       (c.oid is not null) as ok,
       case when c.oid is null then 'missing' when c.relrowsecurity then 'RLS on' else 'RLS OFF' end as detail
from expected e
left join pg_class c on c.relname = e.tbl and c.relnamespace = 'public'::regnamespace
union all
select 'rls ' || e.tbl, coalesce(c.relrowsecurity, false), 'row level security enabled'
from expected e
left join pg_class c on c.relname = e.tbl and c.relnamespace = 'public'::regnamespace
union all
select 'no public policies on ' || e.tbl,
       not exists (select 1 from pg_policies p where p.schemaname = 'public' and p.tablename = e.tbl
                   and ('anon' = any(p.roles) or 'public' = any(p.roles))),
       'anon/public cannot read or write'
from expected e
union all
select 'constraint quran_never_dubbed',
       exists (select 1 from pg_constraint where conname = 'quran_never_dubbed'),
       'Quran segments can never hold TTS audio'
union all
select 'column video_segments.' || col,
       exists (select 1 from information_schema.columns
               where table_schema = 'public' and table_name = 'video_segments' and column_name = col),
       'added in latest migration'
from unnest(array['source_id','quran_suspected','detection_reason','tempo_factor','needs_human_review']) as col
order by 2, 1;
