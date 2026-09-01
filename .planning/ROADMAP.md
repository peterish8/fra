# Roadmap: Financial Research Agent

## Overview

This roadmap converts the specification pack into a dependency-ordered OJT V1 build. It starts with a runnable, authorized modular-monolith foundation; builds the Truth Ledger and conservative entity/source/claim pipeline; adds deterministic financial reconciliation, durable deep research, scores, report UX, versions/comparison, and the weekly watchlist; then closes with security, evaluation, operations, and policy release gates. Each phase is coherent, independently verifiable, and split into two bounded plans.

## Milestone

**OJT V1 — Evidence-backed research workspace**

## Phases

- [x] **Phase 01: Foundation & Quality** — Establish the runnable Next.js/FastAPI/Supabase baseline, auth boundary, schema, RLS, and CI.
- [x] **Phase 02: Workspace & Entity Resolution** — Create persistent report workspaces and resolve legal entities without guessing.
- [x] **Phase 03: Retrieval & Source Ledger** — Add safe provider routing, public extraction, source snapshots, and source-family provenance.
- [ ] **Phase 04: Claim & Verification Core** — Turn evidence into typed facts, atomic claims, verification records, and gated report output.
- [ ] **Phase 05: Financial Reconciliation & Conflicts** — Normalize financial facts, integrate official/fallback data, and explain disagreements.
- [ ] **Phase 06: Durable Orchestration & Deep Verification** — Make research resumable and budgeted, then add adversarial/follow-up/freshness behavior.
- [ ] **Phase 07: Scores & Evidence-led Report UI** — Deliver deterministic score breakdowns and the core report/claim/evidence experience.
- [ ] **Phase 08: Living Reports & Comparison** — Add refresh/version diffs, affected-claim updates, and cohort-aware company comparison.
- [ ] **Phase 09: Weekly Watchlist & Discover** — Build the staged weekly funnel, atomic publication, rank history, and discovery screen.
- [ ] **Phase 10: Hardening, Evaluation & Release** — Prove security, quality, resilience, observability, deployment, and policy readiness.

## Phase Details

### Phase 01: Foundation & Quality
**Goal**: A local user can authenticate, reach a protected backend, and work against a validated PostgreSQL/RLS foundation with CI checks.
**Depends on**: Nothing
**Requirements**: [FND-01, FND-02, FND-03, AUTH-01, AUTH-02, DATA-01, DATA-02, DATA-03]
**Success Criteria** (what must be TRUE):
  1. Frontend and FastAPI health surfaces run locally from typed configuration with request IDs and safe structured logs.
  2. Authenticated and unauthorized access paths are distinguishable and owner checks are enforced server-side.
  3. The baseline schema, constraints, indexes, immutability approach, and RLS policies validate without exposing service-role secrets.
  4. CI runs the documented frontend/backend/schema/API/security smoke gates.
**Plans**: 2 plans

Plans:
- [x] 01-01: Bootstrap application structure, typed configuration, auth boundary, and health endpoints
- [x] 01-02: Establish Truth Ledger schema/RLS, structured observability hooks, and CI quality gates

### Phase 02: Workspace & Entity Resolution
**Goal**: A user can create a report, find it in their library, and resolve the intended legal company or choose among ambiguous candidates.
**Depends on**: Phase 01
**Requirements**: [RPT-01, RPT-02, RPT-03, ENT-01, ENT-02, ENT-03, ENT-04, ENT-05]
**Success Criteria** (what must be TRUE):
  1. Report creation persists subject/focus/depth and returns a stable report identifier.
  2. Library/sidebar search, filtering, opening, and soft deletion respect ownership and preserve shared evidence.
  3. Resolution uses aliases, domains, tickers, jurisdictions, and registry evidence and returns explicit confidence/status.
  4. Ambiguous or unconfirmed identity stops high-confidence research and shows actionable candidates/status.
  5. Legal records and entity relationships retain source, freshness, dates, and scope.
**Plans**: 2 plans

Plans:
- [x] 02-01: Implement report workspace CRUD, library queries, soft deletion, and protected API contracts
- [x] 02-02: Implement entity resolution, registry adapters, relationship history, and ambiguity UX

### Phase 03: Retrieval & Source Ledger
**Goal**: The system can safely discover and extract permitted public evidence while preserving source lineage and independence.
**Depends on**: Phase 02
**Requirements**: [SRC-01, SRC-02, SRC-03, SRC-04, SRC-05, SRC-06, SRC-07]
**Success Criteria** (what must be TRUE):
  1. Domain services call capability interfaces, not provider-specific response shapes, and normalize provider outcomes.
  2. Search/extraction fallback behavior records request metadata, cost/latency, source identity, and explicit restricted/unavailable outcomes.
  3. SSRF and redirect protections block internal/private targets before and during retrieval.
  4. Company-owned pages are preserved as self-reported origin evidence and excluded from independent verification for the same claims.
  5. Repeated/syndicated/shared-root sources collapse into source families without losing provenance.
**Plans**: 2 plans

Plans:
- [x] 03-01: Build provider contracts, search/extraction adapters, safe URL policy, and fixture tests
- [x] 03-02: Build source/snapshot ledger, domain verification, self-reported capture, and source-family lineage

### Phase 04: Claim & Verification Core
**Goal**: Retrieved evidence becomes typed facts and atomic claims whose semantic verification and publication status are deterministic and inspectable.
**Depends on**: Phase 03
**Requirements**: [CLM-01, CLM-02, CLM-03, CLM-04, CLM-05, CLM-06, CLM-07]
**Success Criteria** (what must be TRUE):
  1. Structured extraction rejects invalid output and preserves explicit evidence spans and original values.
  2. Compound prose is decomposed into atomic claim versions with evidence relations and source independence flags.
  3. Semantic verification produces normalized outcomes without using outside knowledge to rescue weak citations.
  4. Verdict rules keep unverified, insufficient, partial, contradicted, stale, and verified states distinct.
  5. Report publication is blocked when citation, identity, deterministic-check, critical-conflict, or claim-mapping gates fail.
**Plans**: 2 plans

Plans:
- [x] 04-01: Implement validated LLM envelopes, fact extraction, atomic claim construction, and evidence mapping
- [ ] 04-02: Implement semantic verification, verdict rules, synthesis claim mapping, and publication gates

### Phase 05: Financial Reconciliation & Conflicts
**Goal**: Financial facts are comparable only after deterministic normalization, and genuine disagreements are classified rather than averaged away.
**Depends on**: Phase 04
**Requirements**: [FIN-01, FIN-02, FIN-03, FIN-04, FIN-05, FIN-06, VER-01, VER-02]
**Success Criteria** (what must be TRUE):
  1. Money/unit/sign/period/formula fixtures produce deterministic normalized results with inputs and versions.
  2. Official filing/XBRL facts are preferred where applicable and commercial providers are recorded as fallback/cross-check sources.
  3. Like-for-like comparison distinguishes real value conflict from period, currency, accounting, definition, scope, and restatement differences.
  4. Conflict groups retain members, severity, classification, explanation, resolution status, and unresolved uncertainty.
**Plans**: 2 plans

Plans:
- [ ] 05-01: Build financial taxonomy/normalizers, deterministic calculators, and official/fallback adapters
- [ ] 05-02: Build reconciliation, conflict grouping/classification, and labeled conflict fixtures

### Phase 06: Durable Orchestration & Deep Verification
**Goal**: Research runs survive worker/provider failures and can spend bounded resources on deep, adversarial, freshness-driven follow-up.
**Depends on**: Phase 05
**Requirements**: [RUN-01, RUN-02, RUN-03, RUN-04, VER-03, VER-04, VER-05, VER-06]
**Success Criteria** (what must be TRUE):
  1. Jobs are claimed with leases, retry safely, and checkpoint every pipeline stage in PostgreSQL.
  2. Duplicate triggers do not duplicate work, report versions, or published truth records.
  3. Cost, page/search/deep-call/loop limits and provider degradation become explicit partial outcomes.
  4. Deep and adversarial research seek weakening/counterevidence, attach to existing claim lineage, and never override deterministic gates.
  5. Freshness marks affected claims and refresh planning can stop cleanly on no progress or budget exhaustion.
**Plans**: 2 plans

Plans:
- [ ] 06-01: Implement durable queue, stage checkpoints, leases, idempotency, retries, budgets, and provider health
- [ ] 06-02: Implement deep-research routing, adversarial verification, follow-up loops, and freshness policies

### Phase 07: Scores & Evidence-led Report UI
**Goal**: Users can read a report and understand evidence quality through separate, explainable score cards and claim inspection.
**Depends on**: Phase 06
**Requirements**: [SCO-01, SCO-02, SCO-03, SCO-04, SCO-05, UI-01, UI-02, UI-03, UI-04, UI-05]
**Success Criteria** (what must be TRUE):
  1. Claim, research, evidence, disclosure, and business/watchlist scores are separate, versioned, coverage-aware, and drill-downable.
  2. The report reader and claims table expose origin, verdict, materiality, confidence, freshness, source families, and limitations.
  3. The inspector answers why a claim received its verdict/score using evidence, numeric/temporal/adversarial checks, conflicts, and history.
  4. Missing website/data, provider degradation, ambiguity, loading, empty, and error states are honest and actionable.
  5. Financial, conflict, and source displays are dense but readable and evidence-linked.
**Plans**: 2 plans

Plans:
- [ ] 07-01: Implement versioned score engines, coverage/reliability gates, and deterministic breakdown APIs
- [ ] 07-02: Implement report reader, quality cards, claims table, inspector, financial/conflict/source views, and honest states

### Phase 08: Living Reports & Comparison
**Goal**: A report can be refreshed without erasing history, and multiple companies/versions can be compared without hiding incompatibility.
**Depends on**: Phase 07
**Requirements**: [RPT-04, UI-06, UI-07, CMP-01, CMP-02]
**Success Criteria** (what must be TRUE):
  1. Refresh creates a new run/version and keeps prior report, claim, evidence, calculation, and score history readable.
  2. A version diff identifies added, updated, invalidated, stale, newly conflicted, resolved, and score changes with reasons.
  3. A comparison supports two or more companies with normalized, evidence-linked compatible metrics.
  4. Cohort/entity differences, unknowns, and incompatible metrics are labeled rather than rendered as zero/equivalent.
  5. Desktop and mobile/keyboard flows preserve access to report meaning and evidence.
**Plans**: 2 plans

Plans:
- [ ] 08-01: Implement refresh/version persistence, affected-claim planning, history timeline, and diff API/UI
- [ ] 08-02: Implement normalized comparison workspace, cohort warnings, responsive behavior, and accessibility pass

### Phase 09: Weekly Watchlist & Discover
**Goal**: A weekly durable funnel publishes a transparent evidence-backed Research Watchlist only when candidates pass quality gates.
**Depends on**: Phase 08
**Requirements**: [WL-01, WL-02, WL-03, WL-04, WL-05]
**Success Criteria** (what must be TRUE):
  1. Duplicate scheduler events converge on one period-scoped idempotent run.
  2. Candidate discovery, cheap screening, shortlist verification, and finalist deep research use staged budgets and persisted status.
  3. Eligibility and score breakdowns are cohort/stage-aware, evidence-weighted, methodology-versioned, and rank-history aware.
  4. A failed/partial staging run cannot replace the last known-good public list; fewer than 25 is valid.
  5. Discover clearly labels the result as a Research Watchlist and not investment advice.
**Plans**: 2 plans

Plans:
- [ ] 09-01: Implement scheduled watchlist funnel, eligibility, cohort scoring, atomic publication, and rank history
- [ ] 09-02: Implement Discover/watchlist UI, methodology disclosure, filters, quality notes, and degraded states

### Phase 10: Hardening, Evaluation & Release
**Goal**: The product is demonstrably safe, testable, observable, deployable, and honest enough for an OJT release.
**Depends on**: Phase 09
**Requirements**: [SEC-01, SEC-02, SEC-03, SEC-04, QA-01, QA-02, QA-03, QA-04, QA-05, QA-06, OPS-01, OPS-02, POL-01]
**Success Criteria** (what must be TRUE):
  1. Authorization, SSRF, prompt-injection, XSS, secret, quota, provider-payload, and dependency/security gates pass.
  2. Citation coverage, conflict, numeric, entity/source-independence, golden-case, chaos, E2E, accessibility, and responsive evaluations produce recorded evidence.
  3. Logs, traces, metrics, cost accounting, alerts, and run-debug surfaces explain provider/run/publication behavior without secrets.
  4. Staging and production deployment/migration/rollback contracts are documented and exercised with a golden research case.
  5. Methodology, attribution/retention, privacy/terms, and non-advice positioning are ready for the launch decision.
**Plans**: 2 plans

Plans:
- [ ] 10-01: Run security hardening, deterministic/evidence evaluation, chaos tests, and release-quality browser checks
- [ ] 10-02: Complete observability, deployment/rollback, policy documentation, final DoD audit, and OJT demo readiness

## Progress

**Execution Order:** Phases execute in numeric order: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10

| Phase | Plans Complete | Status | Completed |
|---|---:|---|---|
| 01 Foundation & Quality | 2/2 | Complete | 2026-09-01 |
| 02 Workspace & Entity Resolution | 2/2 | Complete | 2026-09-01 |
| 03 Retrieval & Source Ledger | 2/2 | Complete | 2026-09-01 |
| 04 Claim & Verification Core | 1/2 | In progress | 2026-09-01 |
| 05 Financial Reconciliation & Conflicts | 0/2 | Not started | - |
| 06 Durable Orchestration & Deep Verification | 0/2 | Not started | - |
| 07 Scores & Evidence-led Report UI | 0/2 | Not started | - |
| 08 Living Reports & Comparison | 0/2 | Not started | - |
| 09 Weekly Watchlist & Discover | 0/2 | Not started | - |
| 10 Hardening, Evaluation & Release | 0/2 | Not started | - |

---
*Roadmap created: 2026-09-01 from the complete specification pack*  
*Requirement coverage: 79/79 mapped*
