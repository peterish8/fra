# Implementation Backlog

Task IDs are stable references for agents/commits. Priority: P0 critical, P1 core, P2 enhancement.

## Foundation

- **FND-001 P0** Bootstrap Next.js TypeScript app, Tailwind, shadcn/ui, strict lint/typecheck.
- **FND-002 P0** Bootstrap FastAPI app with typed config, health endpoint, structured logs.
- **FND-003 P0** Configure Supabase Auth + backend identity verification.
- **FND-004 P0** Apply baseline schema/migrations and RLS.
- **FND-005 P0** GitHub Actions quality pipeline.
- **FND-006 P1** Sentry + request/run IDs + OpenTelemetry hooks.

## Reports & Entities

- **ENT-001 P0** Report CRUD/library API/UI.
- **ENT-002 P0** Company/alias/domain search.
- **ENT-003 P0** Entity-resolution service with confidence/ambiguity output.
- **ENT-004 P0** SEC adapter.
- **ENT-005 P0** GLEIF adapter.
- **ENT-006 P1** Companies House adapter.
- **ENT-007 P1** India MCA/data.gov.in adapter.
- **ENT-008 P1** Parent/subsidiary/name-history handling.

## Sources & Retrieval

- **SRC-001 P0** Provider adapter interface/status model.
- **SRC-002 P0** Perplexity Search adapter.
- **SRC-003 P1** Brave fallback adapter.
- **SRC-004 P1** Exa search/contents adapter.
- **SRC-005 P0** Firecrawl extraction adapter.
- **SRC-006 P0** Safe URL/SSRF validation.
- **SRC-007 P0** Source/source-snapshot persistence + content hashing.
- **SRC-008 P1** Source-family duplicate/syndication detection.
- **SRC-009 P1** Browser-rendering fallback adapter.

## Claim Pipeline

- **CLM-001 P0** Company-owned claim extractor with structured output schema.
- **CLM-002 P0** Fact extractor/metric taxonomy.
- **CLM-003 P0** Atomic claim builder.
- **CLM-004 P0** Evidence mapping.
- **CLM-005 P0** Semantic citation verifier.
- **CLM-006 P0** Claim verdict decision engine.
- **CLM-007 P0** Publication gate.

## Financial Validation

- **FIN-001 P0** Money/unit normalizer (million/billion/lakh/crore).
- **FIN-002 P0** Period/fiscal normalizer.
- **FIN-003 P0** Percentage/growth/margin calculators.
- **FIN-004 P1** EODHD adapter.
- **FIN-005 P1** Twelve Data fallback.
- **FIN-006 P1** SEC XBRL/company-facts structured retrieval.
- **FIN-007 P1** Financial reconciliation rules.

## Conflicts & Deep Verification

- **VER-001 P0** Conflict candidate grouping.
- **VER-002 P0** Conflict classification/resolution rules.
- **VER-003 P1** Gemini Deep Research adapter.
- **VER-004 P1** Adversarial research planner/verifier.
- **VER-005 P1** Bounded follow-up research loop.
- **VER-006 P1** Freshness engine.

## Scoring

- **SCR-001 P0** Claim confidence v1 deterministic engine.
- **SCR-002 P1** Evidence coverage engine.
- **SCR-003 P1** Disclosure reliability v1 with sample-size gate.
- **SCR-004 P1** Report research confidence.
- **SCR-005 P2** Cohort business/financial scoring.

## Report UI

- **UI-001 P0** App sidebar/report library.
- **UI-002 P0** Research creation + entity ambiguity flow.
- **UI-003 P0** Research progress timeline.
- **UI-004 P0** Report reader/current quality cards.
- **UI-005 P0** Claims-vs-evidence table.
- **UI-006 P0** Claim inspector drawer.
- **UI-007 P1** Financial tables/charts with evidence drill-down.
- **UI-008 P1** Conflicts screen.
- **UI-009 P1** Sources screen.
- **UI-010 P1** History/version diff.
- **UI-011 P1** Comparison workspace.

## Jobs & Living Reports

- **JOB-001 P0** Durable Postgres job queue/worker lease.
- **JOB-002 P0** Research stage checkpointing/resume.
- **JOB-003 P0** Idempotent refresh -> new report version.
- **JOB-004 P1** Affected/stale claim refresh planning.
- **JOB-005 P1** Provider circuit breakers/cost budget.

## Weekly Watchlist

- **WL-001 P1** Weekly scheduler/idempotent run.
- **WL-002 P1** Broad candidate discovery.
- **WL-003 P1** Eligibility/entity dedupe.
- **WL-004 P1** Cheap screening stage.
- **WL-005 P1** Medium/deep finalist research.
- **WL-006 P1** Cohort-aware watchlist score v1.
- **WL-007 P1** Atomic publish + previous rank delta.
- **WL-008 P1** Discover/watchlist UI.

## Security/Quality

- **SEC-001 P0** Authorization/RLS integration tests.
- **SEC-002 P0** SSRF test corpus.
- **SEC-003 P0** Prompt-injection fixture tests.
- **SEC-004 P1** Rate limiting/quotas.
- **SEC-005 P1** CSP/XSS hardening.
- **QA-001 P0** Citation verification benchmark.
- **QA-002 P0** Conflict benchmark >=90% target.
- **QA-003 P0** Numeric validator benchmark.
- **QA-004 P1** Entity resolution benchmark.
- **QA-005 P1** Chaos/provider outage tests.
- **QA-006 P1** E2E accessibility/responsive suite.

