-- Analyst workflow extension: research modes and user-owned thesis posture.
-- Apply after the baseline schema. This migration never changes canonical
-- claims, evidence, source snapshots, or their verification history.

alter table reports add column if not exists research_mode text not null default 'INITIATION'
  check (research_mode in ('INITIATION','UPDATE','EARNINGS','EVENT','SECTOR','DILIGENCE'));

create table if not exists report_thesis_points (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references reports(id) on delete cascade,
  owner_user_id uuid not null references profiles(id) on delete cascade,
  statement text not null check (length(trim(statement)) between 8 and 2000),
  falsifier text not null check (length(trim(falsifier)) between 8 and 2000),
  materiality materiality_level not null default 'MEDIUM',
  status text not null default 'OPEN'
    check (status in ('OPEN','SUPPORTED','WEAKENED','UNCHANGED')),
  review_note text check (review_note is null or length(review_note) <= 2000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists report_thesis_points_report_updated_idx on report_thesis_points(report_id, updated_at desc);
create index if not exists report_thesis_points_owner_idx on report_thesis_points(owner_user_id, updated_at desc);

create table if not exists report_thesis_point_claims (
  thesis_point_id uuid not null references report_thesis_points(id) on delete cascade,
  claim_version_id uuid not null references claim_versions(id) on delete restrict,
  relationship text not null default 'RELEVANT'
    check (relationship in ('SUPPORTS','WEAKENS','RELEVANT')),
  created_at timestamptz not null default now(),
  primary key(thesis_point_id, claim_version_id)
);

alter table report_thesis_points enable row level security;
alter table report_thesis_point_claims enable row level security;

create policy "users read own thesis points" on report_thesis_points for select using (auth.uid() = owner_user_id);
create policy "users create own thesis points" on report_thesis_points for insert with check (auth.uid() = owner_user_id);
create policy "users update own thesis points" on report_thesis_points for update using (auth.uid() = owner_user_id);
create policy "users read own thesis claim links" on report_thesis_point_claims for select using (
  exists (select 1 from report_thesis_points where id = thesis_point_id and owner_user_id = auth.uid())
);
create policy "users manage own thesis claim links" on report_thesis_point_claims for all using (
  exists (select 1 from report_thesis_points where id = thesis_point_id and owner_user_id = auth.uid())
) with check (
  exists (select 1 from report_thesis_points where id = thesis_point_id and owner_user_id = auth.uid())
);
