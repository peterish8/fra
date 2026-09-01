-- Phase 03-02: durable source identity, retention, and family lineage.
-- This is forward-only and preserves the immutable snapshot baseline.

alter table sources add column identity_key text;
update sources
set identity_key = coalesce(
  nullif(external_document_id, ''),
  nullif(canonical_url, ''),
  'source:' || id::text
)
where identity_key is null;
alter table sources alter column identity_key set not null;
create unique index sources_identity_key_uq on sources(identity_key);

alter table source_snapshots
  add column retention_mode text not null default 'METADATA_ONLY'
  check (retention_mode in ('FULL_TEXT', 'EXCERPT_ONLY', 'METADATA_ONLY', 'STORAGE_REFERENCE'));

create table source_families (
  id uuid primary key default gen_random_uuid(),
  canonical_root text not null,
  family_type text not null default 'INDEPENDENT',
  explanation text,
  created_at timestamptz not null default now(),
  unique(canonical_root, family_type)
);

create table source_family_members (
  source_family_id uuid not null references source_families(id) on delete cascade,
  source_id uuid not null references sources(id) on delete cascade,
  membership_reason text not null,
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  created_at timestamptz not null default now(),
  primary key (source_family_id, source_id),
  unique(source_id)
);

alter table source_families enable row level security;
alter table source_family_members enable row level security;
create policy "service role writes source families" on source_families for all to service_role using (true) with check (true);
create policy "service role writes source family members" on source_family_members for all to service_role using (true) with check (true);
revoke all on source_families, source_family_members from anon, authenticated;
