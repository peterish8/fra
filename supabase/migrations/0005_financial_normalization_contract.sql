-- Phase 05-01: retain financial source representations alongside normalized values.

alter type provider_status add value if not exists 'TIMEOUT';

alter table facts
  add column original_numeric_value numeric(38,12),
  add column original_currency char(3),
  add column original_unit text,
  add column normalized_numeric_value numeric(38,12),
  add column normalized_currency char(3),
  add column normalized_unit text,
  add column provider_request_id uuid references provider_requests(id) on delete set null;

-- Financial facts must retain either a source observation or a declared absence;
-- no default converts an unreported amount to zero.
alter table facts
  add constraint facts_normalized_representation_check
    check (
      normalized_numeric_value is not null
      or original_numeric_value is not null
      or raw_value_text is not null
      or text_value is not null
    );

create index facts_provider_request_idx on facts(provider_request_id);
create index facts_company_metric_period_normalized_idx
  on facts(company_id, metric_code, period_end desc, normalized_currency, normalized_unit);

create table calculation_facts (
  calculation_id uuid not null references calculations(id) on delete cascade,
  fact_id uuid not null references facts(id) on delete restrict,
  input_name text not null,
  created_at timestamptz not null default now(),
  primary key (calculation_id, fact_id)
);
create index calculation_facts_fact_idx on calculation_facts(fact_id);

alter table calculation_facts enable row level security;
create policy "service role writes calculation facts" on calculation_facts
  for all to service_role using (true) with check (true);
revoke all on calculation_facts from anon, authenticated;

create trigger calculations_immutable before update or delete on calculations
  for each row execute function reject_immutable_truth_mutation();
