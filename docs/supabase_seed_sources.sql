insert into public.data_sources (
  id,
  name,
  platform,
  cadence_minutes,
  targets,
  min_score,
  material_strategy,
  credential_key,
  credential_file,
  enabled
) values (
  'x-growth-ai',
  'X Growth AI Sources',
  'x',
  30,
  '["levelsio", "lennysan", "Patticus", "marc_louvion", "tdinh_me"]'::jsonb,
  70,
  'download_media',
  'X_BEARER_TOKEN',
  '/Users/bytedance/personal.config',
  true
)
on conflict (id) do update set
  name = excluded.name,
  platform = excluded.platform,
  cadence_minutes = excluded.cadence_minutes,
  targets = excluded.targets,
  min_score = excluded.min_score,
  material_strategy = excluded.material_strategy,
  credential_key = excluded.credential_key,
  credential_file = excluded.credential_file,
  enabled = excluded.enabled;
