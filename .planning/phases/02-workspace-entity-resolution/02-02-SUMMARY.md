---
phase: 02-workspace-entity-resolution
plan: 02
status: complete
requirements: [ENT-01, ENT-02, ENT-03, ENT-04, ENT-05]
---

# Phase 02 Plan 02 Summary

## Delivered

- Typed entity-query, candidate, match-reason, and resolution contracts with conservative deterministic scoring.
- Explicit `RESOLVED`, `AMBIGUOUS`, and `UNCONFIRMED` outcomes; only resolved identity enables high-confidence research.
- Identifier handling for canonical/former/common names, jurisdiction, ticker/exchange, official domain, registry ID, and LEI, with explainable confidence and evidence references.
- Registry normalization seam covering official success, current/stale freshness, no-result, rate-limit, restricted, temporary/permanent, and parse-failure outcomes without negative identity conclusions.
- Relationship-history normalization preserving parent/subsidiary, former-name, acquisition, and merger records with entity scope, effective dates, and evidence references.
- Authenticated `/v1/companies/resolve` boundary and accessible candidate-selector UI that requires explicit selection before research.
- OpenAPI and API-spec coverage for the resolution response contract.

## Verification Evidence

- Backend: 124 tests passed; Ruff format/check and mypy strict checks passed.
- Entity contract: 18 resolver/registry/relationship tests passed after the Terra-owned router registration; unauthenticated resolution returned the expected `UNAUTHENTICATED` envelope.
- Frontend: 11 Vitest tests passed; typecheck, ESLint, and production build passed.
- OpenAPI validation passed in the backend environment.
- No live registry/provider calls or paid credentials used.

## Explicitly Deferred

- Concrete credentialed SEC/Companies House/MCA/GLEIF network adapters and live registry licensing remain deployment work; this plan establishes the normalized capability seam and fixture behavior.
- Candidate retrieval and relationship/legal-record persistence remain PostgreSQL repository work behind the typed domain boundary; no in-memory state is presented as durable production truth.
- Live Supabase/RLS execution remains blocked by the unavailable Docker Desktop Linux daemon.

## Commits

- `a0988cb` — entity-resolution red contracts and fixtures
- `37ba297` — resolver, registry, relationship, and authenticated API boundaries
- `0b3aa3a` — ambiguity and unconfirmed identity UI
- `4cd77ac` — Terra router integration and API contract synchronization
