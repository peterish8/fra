# Provider Routing, Fallbacks & Cost Controls

## 1. Principle

Providers are interchangeable evidence/retrieval mechanisms. No external AI/search provider is the final authority. The system evaluates the **underlying sources** and stores provider lineage.

## 2. Recommended V1 Provider Map

| Need | Primary | Fallback 1 | Fallback 2 | Notes |
|---|---|---|---|---|
| Web discovery | Perplexity Search API | Brave Search API | Exa Search | Raw results preferred over provider-generated prose. |
| Deep independent research | Gemini Deep Research | Custom multi-search loop | Optional second research provider | Expensive; use on deep/high-materiality stages. |
| Company website extraction | Firecrawl | Exa Contents | Browserless/Zyte permitted render | Public pages only. |
| JS-heavy public pages | Browserless | Zyte | Apify Actor if appropriate | No auth/CAPTCHA bypass. |
| US legal/financial filings | SEC EDGAR/XBRL | — | GLEIF/OpenCorporates for identity only | Official source first. |
| UK registry | Companies House | GLEIF | OpenCorporates | Official source first. |
| India registry | MCA/data.gov.in official datasets/adapters | GLEIF | OpenCorporates | Track dataset freshness. |
| Global legal identity | Country adapter | GLEIF | OpenCorporates | Never claim legal status from weak web source if registry unavailable. |
| Structured financials | Official filing/XBRL | EODHD | Twelve Data | Commercial API is cross-check/fallback. |
| News/events | Perplexity/Brave | GDELT | Exa | Deduplicate PR syndication. |
| Startup/private discovery | Optional Crunchbase | Optional Dealroom | independent web | Paid licensing may gate use. |

## 3. Provider Interface

All adapters return normalized statuses:
- `SUCCESS`
- `NO_RESULTS`
- `RATE_LIMITED`
- `ACCESS_RESTRICTED`
- `PARSE_FAILED`
- `TIMEOUT`
- `TEMPORARY_FAILURE`
- `PERMANENT_FAILURE`

Each result records latency, estimated cost, provider request ID, safe metadata and retrieval time.

## 4. Web Discovery Routing

### Standard search
1. Perplexity Search.
2. If no/low-quality results or outage: Brave.
3. If semantic/document discovery is still weak: Exa.
4. Optional Tavily as additional fallback after evaluation.

### Independent verification of a self-reported claim
- Exclude the company-owned domain(s).
- Prefer regulator/government/filing domains where relevant.
- Require source-family diversity rather than provider diversity.

### Government-specific research
Use direct official API/registry adapter instead of generic search whenever available.

## 5. Extraction Routing

```text
Public URL
 -> safe URL validation / DNS resolution / SSRF guard
 -> simple HTTP/extractor if implemented
 -> Firecrawl
 -> Exa Contents
 -> browser-rendering provider for JS-heavy pages
 -> SOURCE_UNAVAILABLE/ACCESS_RESTRICTED
```

Stop if authentication/paywall/CAPTCHA/private access is required. Do not escalate into bypass behavior.

## 6. Registry Routing

```text
Entity + jurisdiction
 -> official country adapter
 -> GLEIF
 -> OpenCorporates
 -> high-quality independent identity evidence
 -> UNCONFIRMED
```

If official API is temporarily unavailable, cached last-verified registry snapshot may be shown with explicit age/staleness.

## 7. Financial Routing

For reported public-company numbers:
1. official filing/XBRL when available
2. structured provider A
3. structured provider B
4. company statement as origin/context, not independent cross-check

If providers disagree, do not average. Run metric/period/currency/entity-scope reconciliation.
Persist every usable official and commercial observation with its source and
provider-request lineage; fallback selection only chooses the next retrieval
attempt and never overwrites a prior observation.

## 8. Deep Research Routing

Use Gemini Deep Research for:
- user-selected `DEEP` research
- high-materiality unresolved claims
- weekly finalists only
- complex competitive/risk questions where many sources are needed

Do not run expensive deep research across the entire weekly candidate universe.

Deep output is evidence discovery only. It cannot set a claim verdict or
replace semantic, numeric, temporal, entity-scope, or conflict verification.
Adversarial follow-up is reserved for unresolved material claims, high-authority
conflicts, failed deterministic checks, and low-independence evidence.

## 9. Weekly Cost Funnel

Illustrative funnel:
```text
300–500 discovered candidates
 -> cheap entity/news/financial screen
100–200 viable
 -> medium verification
40–75 shortlist
 -> deep research on 25–40 finalists
 -> publish up to 25 qualified entries
```

Budgets are configuration, not hard-coded assumptions.

## 10. Cost Controls

Per research run:
- `max_cost_usd`
- provider-specific call/search limits
- max deep-research calls
- max follow-up loops
- max pages per domain
- cached fresh source reuse

When budget is exhausted:
- stop non-critical follow-up
- persist partial research
- mark `COST_BUDGET_EXCEEDED` limitation
- never fabricate missing evidence

## 11. Retry Policy

Retry only:
- timeouts
- transient 5xx
- explicit retryable provider errors
- rate limit after `Retry-After`/backoff

Do not retry:
- auth failure due to invalid key without config intervention
- access restriction
- invalid URL/request
- permanent parsing/schema error without adapter fallback

Use exponential backoff + jitter and per-provider circuit breakers.

## 12. Caching/Freshness

Cache by:
- canonical URL/document ID + content hash
- entity/registry identifier
- provider query fingerprint where permitted

Reuse only if freshness policy allows. A cache hit must retain original retrieved time and expose age.

## 13. Source Family Rules

Provider output can point to the same underlying origin. Maintain relationships such as:
- syndicated from
- quotes
- derived from company press release
- duplicate content

Confidence uses independent root source families.

## 14. Current Provider Documentation Basis

Implementation should consult current official provider docs before coding because API shapes/pricing change. Starting references:
- Perplexity Search API: https://docs.perplexity.ai/docs/search/quickstart
- Gemini Deep Research: https://ai.google.dev/gemini-api/docs/deep-research
- SEC developer resources: https://www.sec.gov/about/developer-resources
- Companies House API: https://developer.company-information.service.gov.uk/
- GLEIF API: https://www.gleif.org/en/lei-data/gleif-api/
- India OGD/MCA Company Master Data: https://www.data.gov.in/catalog/company-master-data
- Firecrawl: https://www.firecrawl.dev/
- Exa: https://exa.ai/

## 15. Provider Health

Track rolling metrics per provider/operation:
- success rate
- p50/p95 latency
- rate-limit rate
- parse failure rate
- average cost
- result usefulness/evidence yield

Router may temporarily deprioritize unhealthy providers without changing domain semantics.

## 16. Keyless/public adapters implemented in the local build

The backend includes transport-injectable adapters for direct SEC EDGAR
Company Facts requests and direct GLEIF LEI lookups. SEC requests require only
the `SEC_USER_AGENT` identity string; neither adapter accepts credentials from
the browser. The adapters normalize timeouts, rate limits, malformed payloads,
and unavailable records into the provider contracts. Paid search, extraction,
LLM, and commercial financial adapters remain replaceable and credential-gated.
