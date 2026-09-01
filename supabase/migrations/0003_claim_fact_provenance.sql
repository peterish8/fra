-- Phase 04-01: make validated fact-to-claim provenance durable and append-only.

alter table facts
  add column extraction_metadata jsonb not null default '{}'::jsonb,
  add constraint facts_extraction_confidence_range
    check (extraction_confidence is null or extraction_confidence between 0 and 1);

alter table claim_versions
  add column claim_kind text not null default 'QUALITATIVE'
    check (claim_kind in ('QUALITATIVE', 'QUANTITATIVE', 'HISTORICAL_FACT', 'FORECAST', 'GUIDANCE', 'ESTIMATE')),
  add column extraction_metadata jsonb not null default '{}'::jsonb;

alter table claim_evidence
  add constraint claim_evidence_directness_range
    check (directness is null or directness between 0 and 1);

create table claim_version_facts (
  claim_version_id uuid not null references claim_versions(id) on delete cascade,
  fact_id uuid not null references facts(id) on delete restrict,
  relationship_role text not null default 'SOURCE_FACT',
  created_at timestamptz not null default now(),
  primary key (claim_version_id, fact_id)
);

create index facts_run_created_idx on facts(research_run_id, created_at desc);
create index claim_versions_run_created_idx on claim_versions(research_run_id, created_at desc);
create index claim_evidence_claim_created_idx on claim_evidence(claim_version_id, created_at desc);
create index claim_version_facts_fact_idx on claim_version_facts(fact_id);

alter table claim_version_facts enable row level security;
create policy "service role writes claim version facts" on claim_version_facts for all to service_role using (true) with check (true);
revoke all on claim_version_facts from anon, authenticated;

create trigger facts_immutable before update or delete on facts
  for each row execute function reject_immutable_truth_mutation();
create trigger claim_versions_immutable before update or delete on claim_versions
  for each row execute function reject_immutable_truth_mutation();
create trigger claim_evidence_immutable before update or delete on claim_evidence
  for each row execute function reject_immutable_truth_mutation();
