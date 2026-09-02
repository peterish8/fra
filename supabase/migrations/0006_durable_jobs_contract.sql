-- Phase 06-01: link durable delivery jobs to their resumable research run.

alter table jobs
  add column research_run_id uuid references research_runs(id) on delete cascade;

create index jobs_research_run_idx on jobs(research_run_id, created_at desc);
create index jobs_claimable_idx
  on jobs(status, priority desc, available_at, created_at)
  where status = 'QUEUED';

alter table jobs enable row level security;
create policy "service role owns durable jobs" on jobs
  for all to service_role using (true) with check (true);
revoke all on jobs from anon, authenticated;
