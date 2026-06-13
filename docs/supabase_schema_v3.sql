-- Phase 3: make Airtap collection asynchronous.
-- Airtap cloud-phone tasks can run several minutes, longer than a serverless
-- function's max duration. Runs are now created in a 'pending' state with the
-- Airtap task id, then reconciled to success/failed once the task finishes.

alter table public.data_source_runs
  drop constraint if exists data_source_runs_status_check;

alter table public.data_source_runs
  add constraint data_source_runs_status_check
  check (status in ('pending', 'running', 'success', 'failed'));

alter table public.data_source_runs
  add column if not exists airtap_task_id text not null default '';
