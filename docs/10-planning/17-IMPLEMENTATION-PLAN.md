# Implementation Plan

## Strategy

Build the smallest reliable vertical slice first, then add verification depth. Do not start with 25 providers, global registries, or weekly ranking before the core claim/evidence pipeline works.

The recommended build flow follows **Spec → Plan → Tasks → Implement → Verify**.

## Phase 0 — Repository & Quality Foundation

Deliverables:
- monorepo/repo structure
- Next.js app
- FastAPI app
- Supabase project/local schema tooling
- `.env.example`
- CI
- auth skeleton
- structured logging/request IDs
- AGENTS/docs linked from repo

Exit criteria:
- frontend/backend run locally
- CI green
- authenticated `/me`/basic report endpoint works

## Phase 1 — Report Workspace + Entity Resolution

Build:
- reports/library/sidebar
- company/entity tables
- company search/resolve endpoint
- first registry adapters: SEC/US and one India/UK path depending demo target
- GLEIF fallback
- entity ambiguity UI

Exit criteria:
- create report, resolve legal company, persist registry evidence
- ambiguous names do not auto-merge

## Phase 2 — Retrieval & Source Ledger

Build:
- provider interfaces
- Perplexity Search adapter
- Firecrawl extraction adapter
- source/source_snapshot persistence
- source authority/type classification
- company domain verification
- self-reported claim extraction from public company site
- independent-search domain exclusion

Exit criteria:
- given a company, store self-reported claims and independent sources with provenance

## Phase 3 — Facts, Claims & Verification

Build:
- structured fact extraction
- atomic claim builder
- claim evidence mapping
- semantic verifier
- deterministic numeric validator
- temporal/period validator
- publication gate

Exit criteria:
- first end-to-end verified report with evidence drawer
- 100% citation verification coverage enforced for `VERIFIED`

## Phase 4 — Financial Cross-Checks & Conflicts

Build:
- official filing/XBRL extraction where applicable
- financial API adapter A + B/fallback
- metric taxonomy
- conflict detection/classification
- fact reconciliation rules
- source-family dedupe

Exit criteria:
- financial discrepancies correctly separated from period/currency/scope mismatches
- conflict benchmark approaches required target

## Phase 5 — Confidence, Disclosure Reliability & UI Depth

Build:
- versioned claim-confidence engine
- evidence coverage
- disclosure reliability + sample-size gate
- report quality cards
- claims-vs-evidence table
- conflict screen
- source screen

Exit criteria:
- every displayed score has breakdown/version
- no universal trust score

## Phase 6 — Deep/Adversarial Research + Living Reports

Build:
- Gemini Deep Research adapter
- cost-aware deep routing
- adversarial verifier
- follow-up research loop
- freshness policies
- report refresh
- version history + diff

Exit criteria:
- existing NVIDIA-like report can be refreshed without deleting old version
- affected claims can be revalidated

## Phase 7 — Multi-Company Comparison

Build:
- comparison report type
- normalized metric comparison
- evidence-linked cells
- cohort/entity-type warnings

## Phase 8 — Weekly Watchlist

Build:
- scheduled durable job
- candidate discovery
- eligibility funnel
- cohort-aware scoring
- staged publication
- weekly history/rank delta
- Discover UI

Exit criteria:
- duplicate cron does not duplicate watchlist
- failed staging run cannot replace current public list
- may publish fewer than 25 if quality insufficient

## Phase 9 — Hardening / OJT Evaluation

- labeled citation-verification set
- conflict-detection benchmark >=90%
- citation coverage 100% on verified reports
- numeric validation benchmark
- chaos/provider outage tests
- security review (SSRF, authz, prompt injection, rate limits)
- load testing
- final architecture doc/demo script

## Suggested 8-Week Mapping

### Week 1
Foundation + architecture + DB + report workspace + entity model.

### Week 2
Multi-source retrieval + basic report generation.

### Week 3
Citation verification + numeric/temporal checks + tests.

### Week 4
Conflict detection + structured financial tables + first full demo.

### Week 5
Explainable confidence + disclosure reliability + adversarial/chaos tests.

### Week 6
Follow-up research + multi-company comparison + living report versioning.

### Week 7
Weekly watchlist + observability + performance/cost tuning.

### Week 8
Evaluation metrics, security hardening, documentation, deployment, demo video.

## Solo-Dev/AI-Agent Work Pattern

For each feature:
1. create/choose backlog task
2. agent reads AGENTS + relevant docs
3. agent writes a small implementation plan
4. write/adjust tests first for deterministic behavior
5. implement in isolated branch/worktree where useful
6. run validation commands
7. review diff for architectural/spec drift
8. update docs/OpenAPI/schema if contract changed
9. merge only when Definition of Done passes

Avoid “build the entire app” one-shot prompts. Give agents bounded vertical slices with explicit acceptance criteria.

