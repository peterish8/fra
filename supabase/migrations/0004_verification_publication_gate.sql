-- Phase 04-02: append-only verification records and persisted publication quality.

alter table verifications
  add constraint verifications_score_range
    check (score is null or score between 0 and 100);
create index verifications_claim_type_created_idx
  on verifications(claim_version_id, verification_type, created_at desc);

alter table report_versions
  add column verification_gate jsonb not null default '{}'::jsonb,
  add constraint report_versions_verified_gate_check
    check (
      status <> 'VERIFIED'
      or coalesce((verification_gate ->> 'passed')::boolean, false)
    );
