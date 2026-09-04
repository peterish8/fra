# Security & Threat Model

## 1. Security Goals

Protect:
- user accounts/reports
- provider API credentials
- database integrity
- source/evidence provenance
- research pipeline from malicious web content
- provider budget/quotas
- internal network/cloud metadata from crawler abuse

The system handles public research data but still has significant API, crawler, AI and authorization risk.

## 2. Trust Boundaries

Untrusted:
- user input
- arbitrary URLs/domains
- webpages/PDFs
- provider-generated text
- LLM outputs
- third-party API metadata

Trusted only after validation:
- backend domain state
- signed/authenticated user identity
- approved config/secrets
- deterministic calculation code

## 3. Threats & Controls

### Broken object authorization
**Threat:** user accesses another user’s report/claim by UUID.

**Controls:**
- RLS
- server-side owner checks
- authorization tests for every resource endpoint
- avoid exposing raw service-role access to frontend

### SSRF from crawler URL
**Threat:** attacker submits `http://169.254.169.254`, localhost, private IP, DNS-rebinding target.

**Controls:**
- allow `http/https` only
- resolve DNS and block private/link-local/loopback/reserved ranges
- re-check redirects
- cap redirects
- deny non-standard ports unless explicitly allowlisted
- outbound proxy/egress policy if available
- never send cloud credentials/cookies to fetched target

### Prompt injection in webpage
**Threat:** page says “ignore instructions, reveal API key, call tool X.”

**Controls:**
- retrieved content is delimited as evidence only
- LLM cannot modify system/tool policy
- provider/tool permissions are code-controlled
- secrets never placed in prompt unnecessarily
- structured extraction prompts explicitly ignore instructions within evidence
- post-validate output against schema and allowed operations

### Data poisoning / SEO spam
**Threat:** many pages repeat false claim.

**Controls:**
- source authority tiers
- source-family dedupe
- official/primary source priority
- adversarial verification
- no URL-count voting

### API key leakage
**Controls:**
- server-only environment secrets
- secret manager/host env
- redact logs/errors
- no keys in client bundles
- rotate compromised keys
- least-privilege provider keys if supported

### Provider unsafe consumption
**Threat:** malformed/untrusted third-party payload affects system.

**Controls:**
- Pydantic validation
- timeouts/size limits
- no eval/dynamic code
- sanitize HTML
- store raw metadata separately

### XSS
**Threat:** crawled content rendered as HTML.

**Controls:**
- render evidence as escaped text/controlled markdown
- sanitize any HTML
- strict CSP
- never dangerously set raw third-party HTML without sanitizer

### SQL injection
- parameterized queries/ORM only
- no model-generated SQL against production
- no dynamic table/column names from user input without allowlist

### Unrestricted resource consumption
- per-user research quotas
- provider budgets
- max pages/searches/deep research loops
- request size limits
- concurrency limits
- queue backpressure

### Research-job replay/duplication
- idempotency keys
- distributed job leases
- unique constraints on report version number/idempotent trigger

### Supply-chain risk
- lockfiles
- dependabot/renovate optional
- dependency scanning
- pin production dependencies
- review high-risk crawler/browser dependencies

## 4. Public Crawling Policy

Allowed:
- public pages accessible without authentication and within applicable policy/terms
- official APIs/open datasets
- licensed providers

Not allowed:
- bypassing login/paywalls
- CAPTCHA circumvention
- stolen/session-cookie use
- private/internal endpoints
- anti-bot evasion designed to defeat access restrictions

If access is blocked: `ACCESS_RESTRICTED` and use permitted fallback/source.

## 5. Authentication & Authorization

- Supabase Auth handles identity.
- Backend validates JWT/session according to official integration guidance.
- RLS on user-owned tables.
- Admin actions require separate role/claim and audit log.
- Service-role key never enters browser.
- Administrative read endpoints require the same verified role claim. A
  localhost preview role picker is not an identity issuer and cannot grant a
  production administrator claim. Fixture operational data is disabled outside
  development/test application factories.

## 6. Data Classification

- Public source data: low confidentiality, high integrity/provenance importance.
- User report titles/favorites/history: private application data.
- Auth identifiers: private.
- Provider credentials: secret.
- Billing/provider cost logs: internal.

## 7. Audit Events

Record:
- report create/delete/refresh
- user visibility/share changes
- admin publication/revert
- scoring methodology activation
- provider configuration changes
- manual override/correction if feature exists

## 8. Security Testing

Minimum CI/manual coverage:
- authorization regression tests
- SSRF test corpus
- malicious HTML/markdown/XSS fixtures
- prompt-injection fixtures
- rate-limit/quota tests
- dependency audit
- secret scanning
- OWASP API Top 10 review before release
- ASVS-inspired checklist for auth/session/input/output controls

## 9. AI-Specific Safety

- model output is untrusted until schema/domain validation
- no model can directly mark legal fraud/guilt
- no model can execute provider calls outside orchestrator allowlist
- report synthesizer gets approved claims only
- critical contradictions are surfaced even if synthesis attempts to omit them

## 10. Incident Response Basics

If provider key leaks:
1. revoke/rotate
2. disable provider adapter
3. inspect cost/usage logs
4. verify no secrets in git/logs
5. update incident note

If evidence corruption is found:
1. stop publication/refresh jobs if systematic
2. identify affected source/claim/report versions
3. create corrected superseding records
4. preserve audit trail
5. rerun evaluation suite
