# Technical Requirements Document (TRD)

## 1. Purpose

Define how the PRD is implemented as a reliable, auditable, cost-aware web product. This document is normative for technical behavior unless superseded by an ADR.

## 2. Technology Baseline

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js + TypeScript | Latest stable version pinned at project bootstrap; App Router preferred. |
| Styling/UI | Tailwind CSS + shadcn/ui | Accessible primitives; custom product design tokens. |
| Charts | Recharts | Keep charts simple and evidence-linked. |
| Backend | Python + FastAPI | Async provider I/O; Pydantic contracts. |
| Database | PostgreSQL on Supabase | Canonical durable state. |
| Auth | Supabase Auth | Email/OAuth as product needs. |
| Authorization | Postgres RLS + backend checks | Defense in depth. |
| Background jobs | Postgres-backed durable queue + Python worker | V1 simplicity; must support retries/idempotency. |
| Frontend hosting | Vercel | Static/SSR frontend only; do not run long research jobs in request lifecycle. |
| API/worker hosting | Persistent Python ASGI/worker host | Railway/Render/Fly/etc.; provider-neutral in code. |
| Observability | Structured JSON logs + Sentry + OpenTelemetry-compatible traces | Provider calls and stage timings must be traceable. |
| CI/CD | GitHub Actions | lint, typecheck, tests, build, migrations checks. |

## 3. Architecture Style

- **Modular monolith** with clear domain modules.
- Provider adapters implement stable interfaces; no provider-specific logic leaks into domain services.
- Long-running research is event/stage based, durable, resumable and idempotent.
- Canonical truth model is claim/evidence/fact state in PostgreSQL.
- Report prose is generated from verified structured data and stored as a versioned projection.
- No browser-to-third-party-provider calls.

## 4. Backend Module Boundaries

```text
app/
  api/                 # HTTP routes, auth context, response DTOs
  domain/
    companies/         # canonical entities, aliases, parent/sub relationships
    research/          # runs, stages, plans, follow-up loops
    sources/           # source metadata, snapshots, source families
    facts/             # structured facts/financial metrics
    claims/            # atomic claims, versions, materiality
    verification/      # semantic/numeric/temporal/adversarial/conflict logic
    scoring/           # claim confidence, disclosure reliability, watchlist score
    reports/           # report/version synthesis and diff
    watchlist/         # weekly funnel and ranking
  providers/
    search/
    research/
    extraction/
    registries/
    financial/
    llm/
  jobs/                # durable job records, workers, schedules
  persistence/         # repositories/db access
  security/            # URL validation, secret redaction, prompt isolation
  observability/
  config/
```

## 5. Core Domain Invariants

1. A `Company` may have many aliases/domains/legal registry records.
2. `Source` identifies a publisher/document; `SourceSnapshot` freezes retrieved content/version metadata.
3. `Claim` is stable identity; `ClaimVersion` stores changing wording/value/verdict over time.
4. A claim cannot be `VERIFIED` without at least one qualifying evidence relation and a semantic verification result.
5. A self-reported source cannot satisfy the independent-evidence requirement for the same company's self-reported claim.
6. A published report version records exact claim versions used.
7. `ReportVersion` is immutable after publication except administrative metadata.
8. Provider calls are audit logged and status normalized.
9. Score records include scoring algorithm version.
10. Missing dimensions use `NULL/NOT_APPLICABLE`; do not coerce to zero.

## 6. Research Run State Machine

```text
QUEUED
  -> PLANNING
  -> ENTITY_RESOLUTION
  -> RETRIEVING
  -> EXTRACTING
  -> VERIFYING
  -> RESOLVING_CONFLICTS
  -> FOLLOW_UP_RESEARCH (0..N loops)
  -> SCORING
  -> SYNTHESIZING
  -> READY
```

Any stage can yield `PARTIAL` if non-critical provider failures occur and evidence coverage is below full quality but useful output remains. Fatal failures yield `FAILED`. Stages must checkpoint outputs before transition.

## 7. Job Requirements

- Each job has `job_id`, `idempotency_key`, `job_type`, `status`, `attempt_count`, `available_at`, `lease_until`, `payload`, `last_error`.
- Workers claim jobs using transaction-safe locking (`FOR UPDATE SKIP LOCKED` or equivalent).
- Repeated enqueue with same idempotency key must not create duplicate report versions.
- Exponential backoff with jitter for transient provider failures.
- Rate-limit provider calls globally and per user/run.
- Deep research calls must be cancellable at orchestration level where provider permits.
- Weekly watchlist publishes atomically only after validation; partial staging runs never replace current public watchlist.

## 8. Provider Requirements

Every provider adapter must expose:

```python
class ProviderResult[T]:
    status: ProviderStatus
    data: T | None
    provider_request_id: str | None
    retrieved_at: datetime
    cost_usd_estimate: Decimal | None
    raw_metadata: dict
    error_code: str | None
```

Adapters must implement timeouts, retries only for retryable statuses, rate-limit awareness, and fixture-based contract tests.

## 9. Source Snapshot Requirements

For each retrieved source, store where licensing/policy permits:
- canonical URL/document identifier
- publisher/domain
- title
- source type/authority tier
- published date if known
- retrieved date
- content hash
- extracted text/structured representation or permitted excerpt
- raw provider metadata
- redirect chain
- language
- source-family/origin relationship
- company ownership relation (`SELF_REPORTED`, `INDEPENDENT`, `GOVERNMENT`, etc.)

If full content storage is not permitted, store metadata, hashes, permitted excerpts and retrieval references instead.

## 10. LLM Requirements

- All LLM calls use strict structured outputs validated by Pydantic/JSON Schema when output is machine-consumed.
- Prompts have version identifiers.
- Retrieved webpages/documents are delimited as untrusted evidence and cannot alter system/tool policy.
- LLM output never directly changes report/claim status without deterministic domain validation.
- Financial arithmetic uses deterministic code when formula/inputs are available.
- Synthesis receives approved claim IDs and may not introduce new factual claims.
- If synthesis produces unmatched factual statements, publication validation fails.

## 11. API Requirements

- Versioned REST prefix: `/v1`.
- Authenticated user endpoints require bearer/session auth.
- Resource authorization enforced server-side even with RLS.
- Idempotency header supported for create/refresh operations.
- Long-running requests return `202 Accepted` with run/job identifier.
- Pagination: cursor-based for report/claim/source lists.
- Error response has stable `code`, human-safe `message`, `request_id`, optional field details.
- SSE or polling endpoint for research progress; WebSocket not required for V1.

## 12. Data Requirements

- UUID primary keys.
- UTC timestamps (`timestamptz`).
- Money values stored as high-precision decimal plus original text/unit/currency.
- JSONB only for provider-specific/unstructured metadata; important queryable fields get typed columns.
- Foreign keys and check constraints required.
- Soft-delete user-facing reports if needed; evidence/audit retention follows governance rules.
- Migrations are forward-only in production; destructive migrations require explicit ADR/backup plan.

## 13. Performance Targets

- Dashboard/report-library interactive API p95 < 500 ms excluding cold starts/network anomalies.
- Claim inspector p95 < 700 ms for stored data.
- Report initial render should stream/skeleton quickly; large claim lists paginated/virtualized.
- Research run duration is provider-dependent; UX must show stage progress and not block browser request.
- Cache entity/registry and source content according to freshness policy.

## 14. Reliability Targets

- No single optional provider outage causes total research failure if a configured fallback can satisfy the evidence category.
- Research runs checkpoint after each stage.
- Worker restart resumes queued/leased-expired jobs safely.
- Provider retry storms prevented by circuit breakers/backoff.
- Weekly public watchlist publication is atomic and reversible to previous version.

## 15. Security Requirements

Minimum design target: OWASP ASVS-aligned web controls and OWASP API Security Top 10 review.

Required controls:
- authorization on object IDs
- secure auth/session handling
- server-side secrets
- provider egress allow/deny policy
- SSRF prevention for arbitrary URL extraction
- file size/type validation for future upload support
- prompt-injection isolation
- output encoding/XSS controls
- SQL injection prevention
- rate limiting and quotas
- request size limits
- dependency scanning
- audit logs for sensitive/admin actions

## 16. AI/Research Quality Requirements

- Curated evaluation dataset versioned in repository or private fixture store.
- Citation verification coverage measured separately from correctness.
- Conflict detection benchmarked with labeled examples.
- Numeric validator unit tests include currency/unit/period edge cases.
- Source-independence evaluation includes syndicated articles and shared-root evidence.
- Deep-research output is treated as a retrieval/reasoning source, not final truth.

## 17. Configuration

Provider routing, score weights, freshness thresholds, materiality rules, retry counts and cost budgets must be configuration-driven and versioned. Production changes to scoring methodology must create a new score-version identifier.

## 18. Explicit Non-Requirements

- No microservices in V1.
- No event bus unless measured need emerges.
- No vector database by default.
- No autonomous trading or brokerage actions.
- No restricted-site access bypasses.
- No MCP/plugin layer.

