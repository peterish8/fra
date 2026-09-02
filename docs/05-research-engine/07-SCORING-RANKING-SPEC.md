# Scoring & Ranking Specification

## 1. Why Multiple Scores

Do not expose one universal “trust score.” The product uses separate metrics because they answer different questions.

1. **Claim Confidence** — how strongly is a specific claim supported?
2. **Research Confidence** — how reliable/complete is this report’s evidence?
3. **Disclosure Reliability** — how well do eligible company-made claims survive independent verification?
4. **Financial/Business Score** — what do the company’s fundamentals/momentum show within its cohort?
5. **Watchlist Score** — transparent ranking score for weekly research discovery, not investment advice.

## 2. Claim Confidence v1

Decision verdict is rule-based first. Confidence is explanatory second.

Base dimensions (weights before re-normalization):

| Dimension | Weight |
|---|---:|
| Semantic evidence support | 30 |
| Source authority/context fit | 15 |
| Independent source-family support | 15 |
| Numeric validation | 10 |
| Temporal/period validation | 10 |
| Cross-source agreement | 10 |
| Freshness | 5 |
| Adversarial survival | 5 |

If a dimension is genuinely `NOT_APPLICABLE`, remove its weight and re-normalize. Do not award or subtract arbitrary points.

Material unresolved contradictions apply caps:
- `CRITICAL`: confidence cannot exceed 49 until resolved.
- `HIGH`: cannot exceed 69.

A verified claim should normally require >=85 **plus** rule-gate conditions; score alone cannot create `VERIFIED`.

## 3. Source Authority Scoring

Authority is not a universal rank; score relevance to the fact.

Example defaults:
- government/regulator for registration/legal status: very high
- audited/regulatory filing for reported company financials: very high
- financial API for convenient structured cross-check: medium-high
- reputable independent journalism for events: medium-high
- company website for what the company says: very high as **origin evidence**, low as independent confirmation
- unknown general web: low

This prevents the mistake “government is always more correct about every fact.”

## 4. Research Confidence v1

Compute from:
- weighted claim confidence across material claims
- evidence coverage
- source diversity/independence
- unresolved conflict penalty
- stale evidence penalty
- entity-resolution status
- publication-gate completeness

Example conceptual formula:
```text
quality = weighted mean of eligible material claim confidence
coverage_factor = 0..1
source_diversity_factor = 0..1
penalty = conflicts + staleness + identity uncertainty
research_confidence = quality * sqrt(coverage_factor) * diversity_adjustment - penalty
```

Exact production formula must live in versioned deterministic code/config with unit tests.

## 5. Disclosure Reliability v1

Purpose: measure independently verifiable **self-reported material claims**, not moral trustworthiness.

Eligible claim weights by materiality:
- LOW = 1
- MEDIUM = 2
- HIGH = 4
- CRITICAL = 8

Outcome values:
- VERIFIED = 1.00
- PARTIALLY_SUPPORTED = 0.60
- CONTRADICTED = 0.00
- UNVERIFIED = excluded from reliability numerator/denominator but counted in coverage
- INSUFFICIENT_EVIDENCE = excluded and counted in coverage limitation

```text
reliability = sum(materiality_weight * outcome_value)
              / sum(materiality_weight for independently assessable claims)

coverage = assessed_self_reported_materiality_weight
           / total_self_reported_materiality_weight
```

Display a numerical reliability score only if configurable minimums are satisfied, e.g.:
- >=5 eligible material claims, and
- >=40% weighted independent-assessment coverage.

Otherwise show `NOT_ENOUGH_DATA` with coverage.

A single contradicted `CRITICAL` claim must also produce a prominent material contradiction badge even if the average remains high.

## 6. Financial/Business Scoring

Never compare unlike companies with identical raw formulas.

### Public company cohort v1
Possible components:
- revenue growth/momentum
- profitability/margin quality
- cash flow quality
- balance-sheet resilience
- earnings consistency
- business concentration/risk
- valuation context (optional; carefully labeled)
- evidence quality

### Startup/private cohort v1
Possible components:
- verified funding/capital quality
- revenue/traction evidence where available
- customer/product adoption signals
- hiring/operating momentum
- partnership verification
- market opportunity evidence
- runway/risk signals where available
- disclosure/evidence quality

Missing non-public data is not automatically a negative; use coverage/unknown states.

### Sector-specific models
Banks/insurers require dedicated metric sets. Do not reuse SaaS margins/debt scoring blindly.

## 7. Weekly Watchlist Eligibility

Before ranking, candidate must satisfy:
- entity resolution above threshold
- no unresolved identity collision
- minimum evidence coverage
- enough recent evidence for cohort
- not clearly inactive/dissolved unless watchlist specifically includes distressed entities
- no critical pipeline failure

If fewer than 25 candidates qualify, publish fewer than 25.

## 8. Watchlist Score v1

The watchlist answers: “Which companies are most worth investigating based on current evidence-backed momentum?” not “What should I buy?”

Suggested high-level components after cohort normalization:

| Component | Weight |
|---|---:|
| Financial/operational momentum | 30 |
| Growth/traction evidence | 20 |
| Market/product momentum | 15 |
| Risk resilience | 10 |
| Evidence quality/coverage | 10 |
| Disclosure reliability | 10 |
| Freshness/recency | 5 |

Rules:
- PR/news volume cannot directly dominate market momentum.
- Deduplicate syndicated press.
- Extreme percentage growth from a tiny base is adjusted for scale/base effects.
- Scores normalized within appropriate cohort/sector/stage.
- A company with poor evidence coverage cannot rank highly just because of hype signals.
- Ranking methodology version displayed publicly.

## 9. Rank Stability

Avoid noisy weekly oscillations:
- use rolling windows for momentum components
- cap single-event contribution
- minimum evidence count for large score jumps
- preserve prior rank
- show `NEW`, `UP`, `DOWN`, `UNCHANGED`
- do not artificially keep rankings stable if evidence materially changes

## 10. Explainability UI

Every score card supports drill-down:

```text
Disclosure Reliability 78/100
Coverage 72%

Verified weighted claims      64%
Partially supported           18%
Contradicted                   8%
Unverified/insufficient       10% (coverage limitation)
Material contradiction: 1 HIGH
```

Never show a score without method/version/coverage context accessible to the user.

## 11. Versioning

Store:
- `score_version`
- input claim/fact IDs
- weights/config hash
- output breakdown
- created timestamp

Historical report scores are not recomputed silently when methodology changes. New methodology creates a new score snapshot/version.

## 12. Implemented v1 contract

The backend scoring package implements these dimensions as deterministic pure
engines. Every result carries `score_version`, a SHA-256 `config_hash`, input IDs,
materiality-weighted coverage, and a machine-readable breakdown. Missing dimensions
are re-normalized rather than treated as zero. High and critical unresolved conflicts
cap claim confidence at 69 and 49 respectively. Disclosure Reliability returns
`NOT_ENOUGH_DATA` until its sample and weighted-coverage gates pass, while critical
contradictions remain an explicit badge.
