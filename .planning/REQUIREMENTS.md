# Requirements: Financial Research Agent

**Defined:** 2026-09-01  
**Core Value:** Every important report statement must let a researcher inspect its claim, evidence, conflicts, and confidence.

These requirements turn the PRD, TRD, research specifications, UI specs, security model, quality plan, and existing task backlog into checkable OJT V1 outcomes. They are intentionally implementation-neutral where the source pack has an open decision.

## V1 Requirements

### Foundation, auth, and data

- [x] **FND-01**: The application loads typed, validated configuration from environment names defined in `.env.example`.
- [x] **FND-02**: Frontend and FastAPI backend run locally with health endpoints and structured request/run identifiers.
- [x] **FND-03**: CI runs frontend, backend, schema, OpenAPI, security, and targeted research-quality checks.
- [ ] **AUTH-01**: A user can authenticate through Supabase Auth and retain a valid session across supported app navigation.
- [ ] **AUTH-02**: Every user-owned report/run/claim access path rejects unauthenticated or unauthorized access server-side.
- [x] **DATA-01**: The PostgreSQL schema stores canonical companies, sources/snapshots, facts, claims/evidence, verifications, conflicts, scores, reports, runs, jobs, and audit events.
- [ ] **DATA-02**: User-owned data is protected with RLS plus backend authorization, while shared truth-ledger writes remain server-controlled.
- [x] **DATA-03**: Immutable source snapshots, report versions, verification/calculation records, score snapshots, and audit events are corrected by superseding records where practical.

### Reports and entities

- [x] **RPT-01**: A user can create a persistent report workspace with a title, subject query, focus, and depth.
- [x] **RPT-02**: A user can search, filter, open, and revisit their report library/sidebar.
- [x] **RPT-03**: A user can soft-delete a workspace without destroying shared evidence referenced by other reports.
- [ ] **RPT-04**: A report can expose its current version and immutable version history with exact claim-version references.
- [ ] **ENT-01**: Company search considers canonical names, aliases, tickers, domains, and supported registry identifiers.
- [ ] **ENT-02**: Entity resolution returns `RESOLVED`, `AMBIGUOUS`, or `UNCONFIRMED` with explainable candidate confidence.
- [ ] **ENT-03**: Ambiguous identity pauses expensive research and requires an explicit candidate choice rather than guessing.
- [ ] **ENT-04**: Legal verification stores jurisdiction, legal name, registration identifier/status, retrieval time, freshness, and source.
- [ ] **ENT-05**: Parent/subsidiary, former-name, acquisition, and merger relationships preserve entity scope and effective dates.

### Retrieval and source ledger

- [ ] **SRC-01**: Provider adapters expose normalized statuses, request metadata, latency/cost, retry classification, and retrieval time behind capability interfaces.
- [ ] **SRC-02**: Web discovery routes through the configured primary/fallback search providers and stores underlying results rather than trusting provider prose.
- [ ] **SRC-03**: Public extraction uses safe validation and permitted extractor/browser fallbacks, stopping with explicit restricted/unavailable status when access is blocked.
- [ ] **SRC-04**: Arbitrary URL retrieval blocks private/link-local/loopback/reserved targets, revalidates redirects, caps redirects, and enforces egress rules.
- [ ] **SRC-05**: Each source and immutable snapshot stores canonical identity, publisher/type/authority, ownership relation, dates, hash, permitted excerpt/storage reference, language, redirects, and metadata.
- [ ] **SRC-06**: Official-domain discovery and company-owned pages produce `SELF_REPORTED` origin claims; company content cannot independently verify itself.
- [ ] **SRC-07**: Duplicate, syndicated, quoted, or shared-root content is grouped into source families so provider agreement is not mistaken for source independence.

### Facts, claims, and publication

- [ ] **CLM-01**: Structured LLM extraction returns schema-validated explicit company claims without inventing precision or turning targets into historical facts.
- [ ] **CLM-02**: Structured facts preserve raw representation plus typed metric, value, unit, currency, period, accounting basis, entity scope, source, and extraction confidence.
- [ ] **CLM-03**: Important report statements are represented as one atomic, independently verifiable claim per proposition.
- [ ] **CLM-04**: Every report claim version maps to evidence relations with role, excerpt/location, directness, and independence metadata.
- [ ] **CLM-05**: Semantic verification evaluates only the claim and supplied evidence and returns `PASS`, `PARTIAL`, `FAIL`, or `INSUFFICIENT`.
- [ ] **CLM-06**: Deterministic verdict rules distinguish `VERIFIED`, `PARTIALLY_SUPPORTED`, `CONTRADICTED`, `UNVERIFIED`, `INSUFFICIENT_EVIDENCE`, and `STALE` before confidence display.
- [ ] **CLM-07**: A `VERIFIED` report version is blocked unless citation verification is 100% complete, identity/numeric gates pass, critical conflicts are not hidden, and synthesis facts map to approved claim IDs.

### Financial facts and conflicts

- [ ] **FIN-01**: Financial values normalize million/billion/thousand, lakh/crore, signs, percentages, basis points, and explicit currency conversions while retaining originals.
- [ ] **FIN-02**: Fiscal/calendar periods, quarters, TTM/annual labels, publication dates, and freshness are normalized before comparison.
- [ ] **FIN-03**: YoY/QoQ growth, margins, ratios, totals, tolerances, and divide-by-zero cases are calculated deterministically with formula/version and inputs stored.
- [ ] **FIN-04**: Official filings/XBRL are preferred for applicable reported financial facts and preserve filing/document provenance.
- [ ] **FIN-05**: Configured commercial financial providers provide fallback/cross-check data with normalized failures, cost, and rate-limit behavior.
- [ ] **FIN-06**: Financial disagreements reconcile metric, definition, period, currency, accounting basis, and entity scope before labeling a genuine conflict; no silent averaging occurs.
- [ ] **VER-01**: Comparable fact/claim candidates are grouped into conflict sets with participating records and severity.
- [ ] **VER-02**: Conflicts are classified into the documented mismatch/restatement/value categories and unresolved uncertainty remains visible.

### Durable research and deeper verification

- [ ] **RUN-01**: Research runs execute through durable Postgres-backed jobs with leases, priorities, retry limits, and transaction-safe worker claiming.
- [ ] **RUN-02**: Each research stage persists checkpoint output and restart/lease expiry resumes safely without corrupting truth-ledger history.
- [ ] **RUN-03**: Repeated create/refresh/schedule requests with the same idempotency key do not duplicate expensive work or report versions.
- [ ] **RUN-04**: Provider budgets, per-run limits, backoff/jitter, circuit behavior, cancellation where supported, and explicit partial/budget-exceeded outcomes are enforced.
- [ ] **VER-03**: Deep research is routed only for selected deep/high-materiality/finalist work and is stored as retrieval/reasoning evidence, not final truth.
- [ ] **VER-04**: Eligible high-materiality claims receive bounded adversarial searches for newer, contradictory, alternative-definition, and counterexample evidence.
- [ ] **VER-05**: Evidence gaps trigger bounded targeted follow-up loops that attach to existing claim lineage and stop on sufficiency, budget, retry, or no-progress.
- [ ] **VER-06**: Claim-type freshness policies mark evidence aging/stale/invalidated and drive affected revalidation without erasing historical records.

### Scores and report experience

- [ ] **SCO-01**: Claim Confidence is deterministic, versioned, decomposable, re-normalized for N/A dimensions, and capped by material unresolved conflicts.
- [ ] **SCO-02**: Evidence Coverage reports assessed materiality/source coverage separately from correctness or reliability.
- [ ] **SCO-03**: Disclosure Reliability uses weighted eligible self-reported claims, exposes coverage and sample-size limits, and can show `NOT_ENOUGH_DATA`.
- [ ] **SCO-04**: Research Confidence combines eligible claim quality, coverage, diversity, conflicts, freshness, identity, and gate completeness with a versioned breakdown.
- [ ] **SCO-05**: Financial/Business scoring is cohort/stage-aware, treats missing private data as unknown/coverage limitation, and stores methodology/version.
- [ ] **UI-01**: A report reader shows identity/legal status, overview, financials, growth, risks, developments, competition, claims/evidence, conflicts, sources, and limitations.
- [ ] **UI-02**: A claims-vs-evidence table filters by verdict/origin/materiality/freshness and shows evidence access, source families, confidence, and status labels.
- [ ] **UI-03**: A claim inspector shows exact wording, origin, structured value/period/scope, evidence excerpts, sources, checks, conflicts, adversarial result, score breakdown, and history.
- [ ] **UI-04**: Financial, conflicts, and sources views keep dense data readable and make each material value/claim evidence-linked.
- [ ] **UI-05**: Loading, empty, error, no-website, insufficient-evidence, provider-degraded, and ambiguous-entity states explain next steps without fake precision.

### Versions, comparisons, and watchlist

- [ ] **UI-06**: Users can compare report versions and see added, updated, invalidated, stale, newly conflicted, resolved, and score changes with reasons/evidence.
- [ ] **CMP-01**: Users can compare at least two companies using normalized compatible metrics with evidence-linked cells.
- [ ] **CMP-02**: Comparison UI labels public/private/startup/cohort differences and refuses to present incompatible metrics as identical or missing values as zero.
- [ ] **UI-07**: Core research flows meet WCAG AA targets, keyboard drawer/table use, visible focus, status text/icons, responsive mobile alternatives, and reduced-motion behavior.
- [ ] **WL-01**: A weekly scheduler enqueues one idempotent durable watchlist run for the configured period.
- [ ] **WL-02**: Watchlist research uses broad discovery, cheap screening, shortlist verification, and deep finalist stages within configured budgets.
- [ ] **WL-03**: Eligibility and ranking use entity/evidence thresholds plus cohort/stage-aware, transparent score components and base-effect/rank-stability controls.
- [ ] **WL-04**: Staged watchlist publication is atomic/reversible, preserves rank history, and can publish fewer than 25 rather than lowering quality thresholds.
- [ ] **WL-05**: Discover displays the current Research Watchlist, methodology/version, update time, confidence/coverage, rank movement, filters, and explicit non-advice wording.

### Security, operations, evaluation, and policy

- [ ] **SEC-01**: Authorization regression tests cover every user-owned resource endpoint and report-child access path.
- [ ] **SEC-02**: SSRF, redirect, nonstandard-port, DNS-rebinding, and restricted-access test fixtures pass with no bypass behavior.
- [ ] **SEC-03**: Prompt-injection, unsafe HTML/XSS, secret leakage, schema-invalid provider/LLM payload, and client-bundle secret checks pass.
- [ ] **SEC-04**: Research creation, provider usage, request size, concurrency, and user quotas are rate-limited with human-safe errors.
- [ ] **QA-01**: The citation-verification evaluation measures 100% coverage for verified reports and correctness separately.
- [ ] **QA-02**: The labeled conflict benchmark reaches at least 90% correct detection/classification at the release gate.
- [ ] **QA-03**: Deterministic numeric fixtures reach at least 99% accuracy across units, periods, currencies, signs, rounding, and invalid math.
- [ ] **QA-04**: Golden entity-resolution/source-independence cases measure precision and abstention across jurisdictions, aliases, parent/subsidiary, syndication, and sparse companies.
- [ ] **QA-05**: Chaos tests cover 429s, timeouts, provider outage, worker crash, lease expiry, duplicate cron, budget exhaustion, and temporary DB errors without silent corruption.
- [ ] **QA-06**: Critical browser flows, accessibility, responsive layouts, and large/empty/status datasets are covered by automated/manual E2E checks.
- [ ] **OPS-01**: Run/provider lineage, stage timings, costs, quality metrics, queue health, and publication-gate reasons are visible through structured logs/metrics/traces without secrets.
- [ ] **OPS-02**: Local, preview/staging, and production deployment contracts include migration order, health checks, rollback/revert, secret separation, and scheduled-worker operation.
- [ ] **POL-01**: Public-facing methodology, attribution/retention, privacy/terms, and non-advice wording are documented before launch and match provider licensing constraints.

## V2 Requirements

Deferred until OJT V1 validates the core traceable research pipeline:

- PDF/export/share workflows and notifications for changed/stale reports.
- Additional country registry adapters beyond the initial supported demonstration coverage.
- Vector retrieval, Redis/managed queue, microservice separation, or an event bus unless measured scale/retrieval needs justify a new ADR.
- A second LLM adjudicator or other provider additions unless evaluation demonstrates a need.

## Out of Scope

| Feature | Reason |
|---|---|
| Autonomous trading or brokerage actions | Product is research/discovery tooling, not execution. |
| Personalized buy/sell or suitability recommendations | Avoid financial-advice scope and misleading certainty. |
| Automated fraud/lying labels | Evidence mismatch is not a legal or moral judgment. |
| Login, paywall, CAPTCHA, private endpoint, or anti-bot bypass | Explicitly prohibited by the security and governance contracts. |
| MCP/plugin product layer | ADR-007 fixes server-side provider adapters as the V1 boundary. |

## Traceability

| Requirement group | Phase | Status |
|---|---:|---|
| FND-01..03 | 01 | Complete |
| AUTH-01..02 | 01 | Pending — later report/session flows remain |
| DATA-01, DATA-03 | 01 | Complete |
| DATA-02 | 01 | Implemented contract; live RLS execution blocked |
| RPT-01..03, ENT-01..05 | 02 | RPT-01..03 complete; ENT-01..05 pending |
| SRC-01..07 | 03 | Pending |
| CLM-01..07 | 04 | Pending |
| FIN-01..06, VER-01..02 | 05 | Pending |
| RUN-01..04, VER-03..06 | 06 | Pending |
| SCO-01..05, UI-01..05 | 07 | Pending |
| RPT-04, UI-06..07, CMP-01..02 | 08 | Pending |
| WL-01..05 | 09 | Pending |
| SEC-01..04, QA-01..06, OPS-01..02, POL-01 | 10 | Pending |

**Coverage:**
- V1 requirements: 79
- Mapped to phases: 79
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-01*  
*Last updated: 2026-09-01 after Phase 02 Plan 01 integration*
