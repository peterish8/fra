# ADR-009: Gate administrative usage data by verified identity claim

**Status:** Accepted

## Context

Product review requires a view of account counts and per-user research limits.
That information is operationally sensitive: a visual route hidden in the
frontend, or a browser-selected role, does not provide authorization.

The project already accepts identity only after server-side JWT verification.
The production quota/audit store is not connected in the local preview yet.

## Decision

- `GET /v1/admin/usage-overview` is a read-only endpoint protected by the
  verified `admin` role claim at the backend.
- The endpoint returns privacy-minimised usage projections only: account IDs,
  display labels, roles, research-run allowance, and quota state. It never
  returns provider keys, session tokens, or research content.
- Development and test factories may attach a repository that returns response
  data explicitly marked `FIXTURE`. Staging and production do not receive that
  repository; they return `ADMIN_USAGE_UNAVAILABLE` until a durable aggregate
  source is configured.
- The localhost login role selector is a UI-preview convenience only. It does
  not issue, modify, or substitute for a production identity claim.
- This read-only introduction does not add a schema migration. The durable
  implementation will aggregate from authenticated accounts, research-run
  quota accounting, and audit events through a dedicated repository.

## Consequences

- A user cannot become an administrator merely by editing a browser role value.
- Tests cover authenticated non-admin rejection and verified-admin access.
- A future live repository must preserve the response contract and capture
  operational audit events for any admin mutations added later.
