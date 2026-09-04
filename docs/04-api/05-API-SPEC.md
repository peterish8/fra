# API Specification

## 1. Conventions

- Base path: `/v1`
- JSON request/response bodies.
- Authenticated endpoints use Supabase-issued bearer/session identity.
- Long-running research operations return `202 Accepted`.
- Mutating create/refresh endpoints accept `Idempotency-Key`.
- Cursor pagination: `limit`, `cursor`.
- Every error includes `code`, `message`, `request_id`.

## 2. Core Endpoints

### Reports

#### `POST /v1/reports`
Create a persistent research workspace.

Request:
```json
{
  "title": "NVIDIA — Deep Research",
  "subject": {"query": "NVIDIA", "country_code": "US"},
  "focus": ["financials", "growth", "risks", "disclosure"],
  "depth": "DEEP",
  "research_mode": "INITIATION"
}
```

Response `201`:
```json
{
  "report_id": "uuid",
  "title": "NVIDIA — Deep Research",
  "status": "DRAFT"
}
```

The optional `Idempotency-Key` is scoped to the authenticated user and create
request. Repeating the same key and payload returns the original workspace;
reusing it with a different payload returns `IDEMPOTENCY_CONFLICT`.

#### `GET /v1/reports`
List user reports for sidebar/library.

Filters: `company_id`, `status`, `q`, `cursor`, `limit`. Results are scoped to
the authenticated owner and exclude soft-deleted workspaces.

#### `GET /v1/reports/{report_id}`
Return workspace metadata and current version summary.

#### `DELETE /v1/reports/{report_id}`
Soft-delete user workspace. Must not destroy shared canonical evidence referenced elsewhere.

Opening or deleting a workspace owned by another user is rejected by the
backend authorization boundary; deleted workspaces are not returned by list,
open, or repeat-delete operations.

`research_mode` is one of `INITIATION`, `UPDATE`, `EARNINGS`, `EVENT`,
`SECTOR`, or `DILIGENCE`. It communicates the analyst workflow requested for a
workspace; it neither changes a claim verdict nor grants a report verification
status.

### Analyst workflow extensions

#### `GET|POST /v1/reports/{report_id}/thesis`
List or create analyst-authored thesis points. A point has a proposition and a
falsifier and is owner-scoped. Its status is one of `OPEN`, `SUPPORTED`,
`WEAKENED`, or `UNCHANGED` and is deliberately distinct from the canonical
claim verdict vocabulary.

#### `PATCH /v1/reports/{report_id}/thesis/{thesis_point_id}`
Update an analyst thesis posture or review note. This endpoint cannot mutate
claim text, evidence, calculations, source-family data, or verification.

#### `GET /v1/reports/{report_id}/change-brief?kind=EARNINGS|FILING`
Return a concise source-cited delta brief. Each line item carries at least one
source snapshot reference and all unavailable/live-data limitations remain in
the response rather than being inferred away.

#### `GET /v1/reports/{report_id}/tearsheet`
Return a cited one-page handoff projection. It is research discovery material,
not investment advice; it preserves source limitations and does not turn a
thesis posture into a verified conclusion.

### Research runs

#### `POST /v1/reports/{report_id}/research-runs`
Start initial research or a manual new run.

Request:
```json
{
  "depth": "STANDARD",
  "focus": ["financials", "risks"],
  "max_cost_usd": 5.0
}
```

Response `202`:
```json
{
  "research_run_id": "uuid",
  "status": "QUEUED"
}
```

#### `POST /v1/reports/{report_id}/refresh`
Refresh the living report. Same long-running semantics; can target stale/affected claims.

Optional body:
```json
{
  "mode": "AFFECTED_ONLY",
  "sections": ["financials", "risks"]
}
```

#### `GET /v1/research-runs/{run_id}`
Returns stage, status, progress counters, provider degradation notes and estimated cost.

#### `GET /v1/research-runs/{run_id}/events`
Server-Sent Events stream for progress. Polling endpoint remains the source of truth.

### Entity resolution

#### `GET /v1/companies/search?q=...`
Search canonical entities/aliases/tickers.

#### `POST /v1/companies/resolve`
Resolve a query to candidate legal entities.

Response may be:
```json
{
  "status": "AMBIGUOUS",
  "selected_company_id": null,
  "research_allowed": false,
  "abstention_reason": "Choose the intended legal entity before research begins.",
  "candidates": [
    {
      "company_id":"...",
      "canonical_name":"Meridian Foods Limited",
      "country_code":"IN",
      "entity_type":"PUBLIC_COMPANY",
      "confidence":0.74,
      "match_reasons":[{"code":"ALIAS_MATCH","detail":"The supplied name is a common alias."}],
      "evidence_refs":["registry-mca-meridian-001"]
    }
  ]
}
```

Resolution is conservative: `RESOLVED` is the only state that permits
high-confidence research, while `AMBIGUOUS` requires an explicit candidate
choice and `UNCONFIRMED` asks for more identity evidence. Registry failures
normalize to `LEGAL_ENTITY_UNCONFIRMED`; they never create a negative or fake
company conclusion.

#### `GET /v1/companies/{company_id}`
Canonical identity, registry status, domains and high-level research metadata.

### Report versions

#### `GET /v1/reports/{report_id}/versions`
List immutable versions.

#### `GET /v1/reports/{report_id}/versions/{version_number}`
Full structured report view.

#### `GET /v1/reports/{report_id}/diff?from=2&to=3`
Return added/updated/invalidated/unchanged claims and score changes.

### Claims/evidence

#### `GET /v1/reports/{report_id}/sources`
Owner-authorized, cursor-paginated source lineage for a report. Returns source identity, publisher, authority and ownership classification, source-family explanation, and a retention-safe latest snapshot summary. It never returns retained full text or exposes a snapshot by UUID without proving report ownership through its research-run linkage.

#### `GET /v1/reports/{report_id}/claims`
Filters: `verdict`, `origin`, `materiality`, `freshness`, `section`, `q`.

#### `GET /v1/claims/{claim_version_id}`
Claim details, confidence breakdown, verification summary.

#### `GET /v1/claims/{claim_version_id}/evidence`
Evidence excerpts, source metadata, independence/source-family data, verification results.

#### `GET /v1/reports/{report_id}/conflicts`
Open/resolved conflicts with classification and affected claims.

### Comparisons

#### `POST /v1/comparisons`
Create a comparison workspace using two or more company IDs.

#### `GET /v1/reports/{report_id}/comparison-metrics`
Normalized comparison table with claim/evidence references.

### Weekly Watchlist

#### `GET /v1/watchlists/latest`
Current published watchlist.

#### `GET /v1/watchlists/{watchlist_id}`
Full methodology version, entries and quality notes.

#### `GET /v1/watchlists/{watchlist_id}/entries/{company_id}`
Company score breakdown, evidence coverage and linked report.

## 3. Internal/Admin Endpoints

Not exposed to ordinary users:
- enqueue weekly watchlist
- republish/revert watchlist
- provider-health diagnostics
- retry dead jobs
- scoring config activation
- evaluation suite execution

#### `GET /v1/admin/usage-overview`

Return a read-only, privacy-minimised view of registered-account count, active
accounts, research-run volume, and per-account research-run allowance. It
requires a verified `admin` identity role claim; an authenticated non-admin
receives `ADMIN_REQUIRED`. It never returns provider credentials, access
tokens, raw research data, or provider configuration.

Development and test responses are explicitly labelled `data_mode: FIXTURE`.
Staging and production return `ADMIN_USAGE_UNAVAILABLE` until the durable quota
and audit aggregation repository is configured. The localhost role picker is a
preview control, not an authentication or authorization mechanism.

Protect through admin role/service identity; do not rely on obscurity.

## 4. Publication Gate API Behavior

If a client requests a verified report and gate conditions are unmet, return structured quality state rather than silently labeling it verified:

```json
{
  "report_status": "READY",
  "verification_gate": {
    "passed": false,
    "citation_coverage": 96.4,
    "blocking_claims": 3,
    "critical_conflicts": 1,
    "reasons": ["Citation verification coverage is below 100%."],
    "blockers": ["CITATION_COVERAGE"]
  }
}
```

## 5. Error Model

```json
{
  "error": {
    "code": "ENTITY_AMBIGUOUS",
    "message": "Multiple matching legal entities were found.",
    "request_id": "req_...",
    "details": {"candidate_count": 3}
  }
}
```

Canonical codes include:
- `UNAUTHENTICATED`
- `ADMIN_REQUIRED`
- `ADMIN_USAGE_UNAVAILABLE`
- `FORBIDDEN`
- `NOT_FOUND`
- `VALIDATION_ERROR`
- `ENTITY_AMBIGUOUS`
- `ENTITY_UNCONFIRMED`
- `RESEARCH_ALREADY_RUNNING`
- `COST_BUDGET_EXCEEDED`
- `PROVIDER_DEGRADED`
- `INSUFFICIENT_EVIDENCE`
- `PUBLICATION_GATE_FAILED`
- `RATE_LIMITED`

## 6. Idempotency

`POST /reports`, `POST /research-runs`, `POST /refresh`, and internal scheduled job creation support an idempotency key scoped to user/action. The backend stores response fingerprint/created resource to prevent duplicate expensive research or duplicate report versions.

## 7. API Security

- Never accept arbitrary source URLs without validation/SSRF defenses.
- Object authorization on every `report_id`, `run_id`, `claim_version_id` access.
- Rate-limit expensive research creation separately from read APIs.
- Enforce request/response size bounds.
- No provider credentials returned to frontend.
