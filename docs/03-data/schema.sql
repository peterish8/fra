-- Financial Research Agent — PostgreSQL/Supabase baseline schema
-- This is a starting migration blueprint. Review extensions/RLS against the actual Supabase project before applying.

create extension if not exists pgcrypto;
create extension if not exists pg_trgm;

create type company_entity_type as enum (
  'PUBLIC_COMPANY','PRIVATE_COMPANY','STARTUP','BANK','INSURER','NONPROFIT','STATE_OWNED','SUBSIDIARY','OTHER'
);
create type report_status as enum ('DRAFT','RESEARCHING','READY','VERIFIED','ARCHIVED');
create type run_status as enum ('QUEUED','RUNNING','PARTIAL','READY','FAILED','CANCELLED');
create type run_stage as enum (
  'PLANNING','ENTITY_RESOLUTION','RETRIEVING','EXTRACTING','VERIFYING','RESOLVING_CONFLICTS',
  'FOLLOW_UP_RESEARCH','SCORING','SYNTHESIZING','COMPLETE'
);
create type claim_origin as enum ('SELF_REPORTED','INDEPENDENT','DERIVED','SYSTEM');
create type claim_verdict as enum (
  'UNVERIFIED','VERIFIED','PARTIALLY_SUPPORTED','CONTRADICTED','INSUFFICIENT_EVIDENCE','STALE'
);
create type materiality_level as enum ('LOW','MEDIUM','HIGH','CRITICAL');
create type freshness_state as enum ('CURRENT','AGING','STALE','INVALIDATED');
create type evidence_role as enum ('ORIGIN','SUPPORTS','CONTRADICTS','CONTEXT');
create type verification_type as enum ('SEMANTIC','NUMERIC','TEMPORAL','ADVERSARIAL','SOURCE_AUTHENTICITY','ENTITY_SCOPE');
create type verification_outcome as enum ('PASS','PARTIAL','FAIL','INSUFFICIENT','NOT_APPLICABLE');
create type conflict_status as enum ('OPEN','RESOLVED','ACCEPTED_UNCERTAINTY');
create type provider_status as enum ('PENDING','SUCCESS','NO_RESULTS','RATE_LIMITED','ACCESS_RESTRICTED','PARSE_FAILED','TEMPORARY_FAILURE','PERMANENT_FAILURE');
create type job_status as enum ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED');

create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table companies (
  id uuid primary key default gen_random_uuid(),
  canonical_name text not null,
  entity_type company_entity_type not null default 'OTHER',
  country_code char(2),
  primary_ticker text,
  primary_exchange text,
  status text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index companies_name_trgm_idx on companies using gin (canonical_name gin_trgm_ops);
create index companies_ticker_idx on companies(primary_exchange, primary_ticker);

create table company_aliases (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  alias text not null,
  alias_type text not null default 'COMMON',
  valid_from date,
  valid_to date,
  created_at timestamptz not null default now(),
  unique(company_id, alias)
);
create index company_aliases_trgm_idx on company_aliases using gin (alias gin_trgm_ops);

create table company_domains (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  domain text not null,
  is_official boolean not null default false,
  verification_status text not null default 'UNCONFIRMED',
  verified_by_source_snapshot_id uuid,
  created_at timestamptz not null default now(),
  unique(company_id, domain)
);

create table company_relationships (
  id uuid primary key default gen_random_uuid(),
  from_company_id uuid not null references companies(id) on delete cascade,
  to_company_id uuid not null references companies(id) on delete cascade,
  relationship_type text not null,
  effective_from date,
  effective_to date,
  evidence_source_snapshot_id uuid,
  created_at timestamptz not null default now(),
  check (from_company_id <> to_company_id)
);

create table sources (
  id uuid primary key default gen_random_uuid(),
  canonical_url text,
  external_document_id text,
  publisher text,
  domain text,
  source_type text not null,
  authority_tier text not null,
  ownership_relation text not null default 'INDEPENDENT',
  is_primary_source boolean not null default false,
  language text,
  created_at timestamptz not null default now()
);
create index sources_url_idx on sources(canonical_url);

create table source_snapshots (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id) on delete cascade,
  title text,
  published_at timestamptz,
  retrieved_at timestamptz not null default now(),
  content_hash text not null,
  extracted_text text,
  storage_ref text,
  redirect_chain jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  unique(source_id, content_hash)
);
create index source_snapshots_source_time_idx on source_snapshots(source_id, retrieved_at desc);
create index source_snapshots_hash_idx on source_snapshots(content_hash);

alter table company_domains add constraint company_domains_verified_source_fk
  foreign key (verified_by_source_snapshot_id) references source_snapshots(id) on delete set null;
alter table company_relationships add constraint company_relationships_evidence_fk
  foreign key (evidence_source_snapshot_id) references source_snapshots(id) on delete set null;

create table source_relationships (
  id uuid primary key default gen_random_uuid(),
  from_source_id uuid not null references sources(id) on delete cascade,
  to_source_id uuid not null references sources(id) on delete cascade,
  relationship_type text not null,
  confidence numeric(5,4),
  created_at timestamptz not null default now(),
  check (from_source_id <> to_source_id)
);

create table legal_entity_records (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  registry_name text not null,
  jurisdiction text,
  registration_number text,
  legal_name text not null,
  legal_status text,
  incorporation_date date,
  registered_address jsonb,
  retrieved_at timestamptz not null,
  freshness freshness_state not null default 'CURRENT',
  source_snapshot_id uuid references source_snapshots(id) on delete set null,
  metadata jsonb not null default '{}'::jsonb
);
create unique index legal_entity_registry_number_uq
  on legal_entity_records(registry_name, registration_number)
  where registration_number is not null;

create table reports (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id) on delete cascade,
  title text not null,
  primary_company_id uuid references companies(id) on delete set null,
  report_type text not null default 'COMPANY_RESEARCH',
  focus jsonb not null default '{}'::jsonb,
  status report_status not null default 'DRAFT',
  current_version_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);
create index reports_owner_updated_idx on reports(owner_user_id, updated_at desc);

create table report_companies (
  report_id uuid not null references reports(id) on delete cascade,
  company_id uuid not null references companies(id) on delete cascade,
  role text not null default 'SUBJECT',
  primary key(report_id, company_id)
);

create table research_runs (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references reports(id) on delete cascade,
  trigger_type text not null default 'USER',
  requested_depth text not null default 'STANDARD',
  status run_status not null default 'QUEUED',
  current_stage run_stage,
  config_version text not null,
  prompt_bundle_version text not null,
  max_cost_usd numeric(12,4),
  estimated_cost_usd numeric(12,4) not null default 0,
  error_summary text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);
create index research_runs_report_time_idx on research_runs(report_id, created_at desc);

create table research_run_stages (
  id uuid primary key default gen_random_uuid(),
  research_run_id uuid not null references research_runs(id) on delete cascade,
  stage run_stage not null,
  status text not null,
  checkpoint jsonb not null default '{}'::jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  unique(research_run_id, stage)
);

create table provider_requests (
  id uuid primary key default gen_random_uuid(),
  research_run_id uuid references research_runs(id) on delete cascade,
  provider text not null,
  operation text not null,
  status provider_status not null default 'PENDING',
  provider_request_id text,
  request_fingerprint text,
  latency_ms integer,
  estimated_cost_usd numeric(12,6),
  safe_metadata jsonb not null default '{}'::jsonb,
  error_code text,
  created_at timestamptz not null default now()
);
create index provider_requests_run_idx on provider_requests(research_run_id, created_at);

create table run_sources (
  research_run_id uuid not null references research_runs(id) on delete cascade,
  source_snapshot_id uuid not null references source_snapshots(id) on delete cascade,
  discovered_by_provider_request_id uuid references provider_requests(id) on delete set null,
  purpose text,
  primary key(research_run_id, source_snapshot_id)
);

create table facts (
  id uuid primary key default gen_random_uuid(),
  research_run_id uuid references research_runs(id) on delete set null,
  company_id uuid references companies(id) on delete cascade,
  source_snapshot_id uuid not null references source_snapshots(id) on delete cascade,
  metric_code text,
  fact_type text not null,
  raw_value_text text,
  numeric_value numeric(38,12),
  text_value text,
  currency char(3),
  unit text,
  period_start date,
  period_end date,
  period_label text,
  accounting_basis text,
  entity_scope text,
  extraction_confidence numeric(5,4),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index facts_company_metric_period_idx on facts(company_id, metric_code, period_end desc);

create table claims (
  id uuid primary key default gen_random_uuid(),
  company_id uuid references companies(id) on delete cascade,
  canonical_key text not null,
  category text not null,
  origin claim_origin not null,
  materiality materiality_level not null default 'MEDIUM',
  created_at timestamptz not null default now(),
  unique(company_id, canonical_key)
);

create table claim_versions (
  id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references claims(id) on delete cascade,
  research_run_id uuid references research_runs(id) on delete set null,
  statement text not null,
  structured_value jsonb not null default '{}'::jsonb,
  verdict claim_verdict not null default 'UNVERIFIED',
  freshness freshness_state not null default 'CURRENT',
  supersedes_claim_version_id uuid references claim_versions(id) on delete set null,
  created_at timestamptz not null default now()
);
create index claim_versions_claim_time_idx on claim_versions(claim_id, created_at desc);

create table claim_evidence (
  id uuid primary key default gen_random_uuid(),
  claim_version_id uuid not null references claim_versions(id) on delete cascade,
  source_snapshot_id uuid not null references source_snapshots(id) on delete cascade,
  evidence_role evidence_role not null,
  excerpt text,
  locator jsonb not null default '{}'::jsonb,
  is_independent boolean not null,
  directness numeric(5,4),
  created_at timestamptz not null default now()
);
create index claim_evidence_claim_idx on claim_evidence(claim_version_id);

create table verifications (
  id uuid primary key default gen_random_uuid(),
  claim_version_id uuid not null references claim_versions(id) on delete cascade,
  verification_type verification_type not null,
  outcome verification_outcome not null,
  score numeric(6,3),
  implementation_version text not null,
  model_name text,
  prompt_version text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index verifications_claim_type_idx on verifications(claim_version_id, verification_type);

create table calculations (
  id uuid primary key default gen_random_uuid(),
  claim_version_id uuid not null references claim_versions(id) on delete cascade,
  formula_code text not null,
  formula_version text not null,
  inputs jsonb not null,
  output jsonb not null,
  tolerance jsonb,
  outcome verification_outcome not null,
  created_at timestamptz not null default now()
);

create table conflicts (
  id uuid primary key default gen_random_uuid(),
  research_run_id uuid references research_runs(id) on delete cascade,
  conflict_type text not null,
  severity materiality_level not null default 'MEDIUM',
  status conflict_status not null default 'OPEN',
  explanation text,
  resolution jsonb,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create table conflict_members (
  conflict_id uuid not null references conflicts(id) on delete cascade,
  claim_version_id uuid references claim_versions(id) on delete cascade,
  fact_id uuid references facts(id) on delete cascade,
  primary key(conflict_id, claim_version_id, fact_id),
  check (claim_version_id is not null or fact_id is not null)
);

create table claim_scores (
  id uuid primary key default gen_random_uuid(),
  claim_version_id uuid not null references claim_versions(id) on delete cascade,
  score_version text not null,
  confidence_score numeric(6,3) not null check (confidence_score between 0 and 100),
  breakdown jsonb not null,
  created_at timestamptz not null default now(),
  unique(claim_version_id, score_version)
);

create table disclosure_score_snapshots (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  research_run_id uuid references research_runs(id) on delete set null,
  score_version text not null,
  score numeric(6,3),
  coverage numeric(6,3) not null check (coverage between 0 and 100),
  status text not null,
  breakdown jsonb not null,
  created_at timestamptz not null default now()
);

create table company_score_snapshots (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  research_run_id uuid references research_runs(id) on delete set null,
  score_type text not null,
  score_version text not null,
  score numeric(6,3),
  cohort text,
  breakdown jsonb not null,
  created_at timestamptz not null default now()
);

create table report_versions (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references reports(id) on delete cascade,
  research_run_id uuid references research_runs(id) on delete set null,
  version_number integer not null,
  status report_status not null,
  title text not null,
  executive_summary text,
  sections jsonb not null default '[]'::jsonb,
  research_confidence numeric(6,3),
  evidence_coverage numeric(6,3),
  generated_at timestamptz not null default now(),
  unique(report_id, version_number)
);
create index report_versions_report_idx on report_versions(report_id, version_number desc);

alter table reports add constraint reports_current_version_fk
  foreign key (current_version_id) references report_versions(id) on delete set null;

create table report_version_claims (
  report_version_id uuid not null references report_versions(id) on delete cascade,
  claim_version_id uuid not null references claim_versions(id) on delete restrict,
  section_key text not null,
  display_order integer not null default 0,
  primary key(report_version_id, claim_version_id)
);

create table watchlist_runs (
  id uuid primary key default gen_random_uuid(),
  period_start date not null,
  period_end date not null,
  methodology_version text not null,
  status text not null,
  candidate_count integer not null default 0,
  published_at timestamptz,
  created_at timestamptz not null default now()
);

create table watchlist_entries (
  id uuid primary key default gen_random_uuid(),
  watchlist_run_id uuid not null references watchlist_runs(id) on delete cascade,
  company_id uuid not null references companies(id) on delete cascade,
  cohort text not null,
  rank integer not null,
  score numeric(6,3) not null,
  eligibility jsonb not null,
  score_breakdown jsonb not null,
  previous_rank integer,
  report_version_id uuid references report_versions(id) on delete set null,
  unique(watchlist_run_id, rank),
  unique(watchlist_run_id, company_id)
);

create table jobs (
  id uuid primary key default gen_random_uuid(),
  job_type text not null,
  idempotency_key text not null unique,
  status job_status not null default 'QUEUED',
  priority integer not null default 100,
  payload jsonb not null,
  attempt_count integer not null default 0,
  max_attempts integer not null default 5,
  available_at timestamptz not null default now(),
  lease_until timestamptz,
  leased_by text,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index jobs_ready_idx on jobs(status, priority, available_at);

create table audit_events (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid references profiles(id) on delete set null,
  event_type text not null,
  object_type text,
  object_id uuid,
  request_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index audit_events_object_idx on audit_events(object_type, object_id, created_at desc);

-- RLS baseline
alter table profiles enable row level security;
alter table reports enable row level security;
alter table report_companies enable row level security;

create policy "users read own profile" on profiles for select using (auth.uid() = id);
create policy "users update own profile" on profiles for update using (auth.uid() = id);
create policy "users read own reports" on reports for select using (auth.uid() = owner_user_id);
create policy "users create own reports" on reports for insert with check (auth.uid() = owner_user_id);
create policy "users update own reports" on reports for update using (auth.uid() = owner_user_id);

-- Additional RLS policies should be added for report child tables through secure views/functions or owner joins.
-- Research writes should be performed by trusted backend/service role, not browser clients.
