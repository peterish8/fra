# Research & Verification Specification

## 1. Purpose

This is the core domain specification. The product is not a generic “deep research” wrapper. It is a pipeline that makes company research **traceable, falsifiable, versioned and explainable**.

## 2. Research Object Model

Research is decomposed into:

1. **Entity** — the legal/company identity being researched.
2. **Source** — publisher/document location.
3. **Source Snapshot** — what the source contained at retrieval time.
4. **Fact** — structured data extracted from evidence.
5. **Claim** — atomic proposition about an entity/topic.
6. **Evidence Relation** — supports/contradicts/context/origin.
7. **Verification** — semantic/numeric/temporal/etc. check.
8. **Conflict** — disagreement requiring classification.
9. **Score** — deterministic interpretation of evidence quality.
10. **Report** — human-readable projection over verified claim versions.

## 3. Entity Resolution

### Inputs
- company name
- country/jurisdiction if known
- official domain if supplied
- ticker/exchange if supplied
- registry number/LEI if supplied

### Resolution evidence priority
1. country-specific government/regulatory registry
2. official filing with identity fields
3. GLEIF
4. structured financial identifier provider
5. OpenCorporates
6. high-quality independent sources

### Resolution outcome
- `RESOLVED` when confidence threshold is met.
- `AMBIGUOUS` when multiple candidates remain.
- `UNCONFIRMED` when insufficient evidence exists.

Never silently merge entities solely by name similarity.

## 4. Company-Owned Claim Capture

Company-owned public sources include:
- official website
- investor relations pages
- company press releases
- company-authored blog
- official public filings only when the **statement itself** is company-authored; the filing may still have higher legal/regulatory authority for specific reported facts.

Company-owned statements become claims with `origin=SELF_REPORTED`.

Examples:
- “We serve 10,000 customers.”
- “We operate in 30 countries.”
- “Revenue grew 50%.”
- “Partnered with Google.”

The system must capture exact wording and context. Vague marketing words (`leading`, `best`, `world-class`) are not converted into precise facts unless there is a measurable interpretation.

## 5. Independent Research Plan

For every material self-reported claim, generate verification questions that **exclude the company-owned domain** and seek at least two independent source families when feasible.

Example:
```text
Claim: "Operating in 30 countries"
Search intents:
- regulatory/subsidiary evidence by jurisdiction
- independent reporting of operating markets
- annual filing geography disclosures
- evidence of market exits or reduced footprint
```

For general company research, planner creates intents for:
- legal identity/status
- recent financial performance
- growth/momentum
- profitability/cash/debt where applicable
- business model/segments
- material risks
- recent developments
- competition
- disclosure verification
- unresolved contradictions

## 6. Source Classification

Each source gets:
- source type
- authority tier
- self-reported vs independent relationship
- primary/secondary
- publication date
- retrieval date
- source family/origin
- language
- potential limitation/bias metadata

Suggested authority tiers:
- `A1`: government/regulator
- `A2`: audited/regulatory filing
- `B1`: structured financial provider
- `B2`: institutional independent research
- `C1`: reputable independent journalism/research
- `D1`: company self-reported
- `E1`: general web
- `E2`: weak/unknown

Authority is contextual. For example, a current regulator filing may outrank a stale registry extract for financial figures, while the registry may be authoritative for registration status.

## 7. Source Independence / Fake Consensus

Do not count URLs. Count independent **source families**.

Detect likely common-origin sources through:
- syndication metadata
- canonical publisher attribution
- near-duplicate content hashes/text similarity
- quoted press-release language
- explicit “source: Reuters/AP/etc.” markers
- references/citation graph

If Perplexity and Gemini both cite the same Reuters article, that is one independent source family, not two.

## 8. Fact Extraction

Facts must be typed before important financial reasoning.

Required financial fields when applicable:
- metric code
- raw text
- numeric value
- original unit
- normalized unit
- original currency
- normalized currency if used
- period start/end/label
- accounting basis (`GAAP`, `NON_GAAP`, etc.)
- entity scope (`CONSOLIDATED`, `PARENT`, `SUBSIDIARY`, `SEGMENT`)
- source snapshot ID
- provider request ID when an adapter supplied the observation

The source representation and normalized representation are both durable. A
conversion requires an explicit rate and rate date; the normalized value is
never a replacement for the source value. Derived values record the formula
version and immutable input-fact IDs in addition to their serialized inputs.

Do not coerce unknown values to zero.

## 9. Atomic Claim Construction

One independently verifiable proposition per claim.

Bad:
> The company grew strongly, generated $100M and dominates its market.

Good:
- FY2026 revenue was $100M.
- FY2026 revenue grew 40% YoY.
- Independent source X estimates market share at 65%.

Claims may be:
- direct fact
- derived metric
- forecast/guidance
- estimate
- qualitative risk conclusion

Forecasts/targets must never be presented as realized historical facts.

## 10. Semantic Citation Verification

Verifier input is limited to:
- claim text/structured value
- evidence excerpt/context
- source metadata

Verifier asks: **Does this evidence actually support this exact claim?**

Internal outcomes:
- `PASS`
- `PARTIAL`
- `FAIL`
- `INSUFFICIENT`

The verifier must not use outside knowledge to rescue unsupported evidence.

## 11. Deterministic Numeric Validation

Code validates when possible:
- million/billion/thousand conversions
- lakh/crore conversions
- currency identity and explicit conversions
- negative accounting notation
- percentages
- basis points
- margins
- YoY/QoQ growth
- ratios
- totals/subtotals where input structure is reliable
- tolerance-based rounded comparisons

Store formula code, version, inputs, immutable input-fact references and output.

Example:
```text
Source: 130,497 million USD
Normalized: 130.497 billion USD
Claim: 130.5 billion USD
Tolerance: +/- 0.01 billion
Result: PASS
```

## 12. Temporal Validation

Before comparing values, normalize:
- calendar year vs fiscal year
- quarter labels
- trailing twelve months vs annual
- publication date vs reporting period
- timezone/date formats
- stale vs current evidence

Do not compare Q1 to FY or FY2025 to CY2025 without explicit transformation/labeling.

## 13. Conflict Detection

Facts/claims are candidates for conflict only if they refer to sufficiently comparable dimensions.

Conflict classes:
- `NO_CONFLICT` (including an inspectable `ROUNDING_DIFFERENCE`)
- `VALUE_CONFLICT`
- `PERIOD_MISMATCH`
- `CURRENCY_MISMATCH`
- `SOURCE_DATE_MISMATCH`
- `METHODOLOGY_DIFFERENCE`
- `GAAP_VS_NON_GAAP`
- `ENTITY_SCOPE_DIFFERENCE`
- `RESTATEMENT`
- `DEFINITION_MISMATCH`
- `INSUFFICIENT_EVIDENCE`

The resolver first checks metric definition, period, currency/Fx date, entity
scope, accounting basis, methodology, source date, and explicit restatement
lineage. Only like-for-like observations can become a `VALUE_CONFLICT`.
Source-family roots, not URLs or providers, determine independent support and
conflict severity. If methodologies genuinely differ, represent a
range/uncertainty instead of fabricating a midpoint. A restatement preserves
the older fact and records the superseding fact; it does not erase history.

## 14. Adversarial Verification

Eligible claims: `HIGH`/`CRITICAL` materiality, key report conclusions, or claims with unusually one-sided support.

Adversarial planner searches for:
- explicit contradiction
- newer evidence
- narrower/broader metric definition
- market exits/declines
- regulatory actions
- restatements
- alternative estimates
- counterexamples

Outcome can:
- strengthen confidence
- reduce confidence
- trigger follow-up research
- change claim wording/verdict

## 15. Follow-Up Research Loop

Trigger when:
- claim is material and unsupported/partial
- high-authority sources conflict
- numeric/period validation fails
- source independence is too low
- adversarial search finds credible counterevidence

Loop:
```text
Identify evidence gap
 -> generate targeted query
 -> retrieve independent source(s)
 -> extract/update facts
 -> rerun verification/conflict logic
 -> stop on sufficiency, budget, retry limit, or no-progress
```

No-progress must terminate rather than infinite-loop.

## 16. Claim Verdict Decision Rules

Verdict is determined **before** displaying a numerical confidence score.

### `CONTRADICTED`
Use when strong, comparable, independent evidence directly opposes the claim and conflict is not explained by period/definition/scope.

### `VERIFIED`
Use when:
- direct support exists,
- required independent-evidence rule is satisfied,
- critical numeric/temporal checks pass or are not applicable,
- no unresolved material contradiction remains,
- confidence threshold and coverage requirements pass.

### `PARTIALLY_SUPPORTED`
Use when a weaker/narrower form is supported, estimates differ within plausible methodology bounds, or only part of compound wording is defensible.

### `UNVERIFIED`
Use when evidence was searched but independent support could not be established and no strong contradiction exists.

### `INSUFFICIENT_EVIDENCE`
Use when evidence coverage is too low to assess fairly.

### `STALE`
Use when previously supported evidence no longer meets freshness requirements and has not yet been revalidated.

## 17. Publication Gate

A report version may be `READY` but not `VERIFIED` if any blocking rule fails.

Minimum gate for `VERIFIED`:
- citation verification coverage = 100% for factual claims included in verified sections
- no unmatched factual statements introduced by synthesis
- no unresolved `CRITICAL` conflict hidden from report
- required identity checks complete
- numeric checks complete for deterministic derived financial claims
- report records score/prompt/config versions

## 18. Report Synthesis

Synthesis input:
- approved claim versions
- structured facts
- score explanations
- conflict summaries
- explicit limitations

Synthesis must reference claim IDs in structured output. A post-synthesis factuality checker rejects factual sentences that cannot map to approved claim IDs.

## 19. Freshness

Freshness policies are claim-type specific and configurable.

Examples:
- market price: minutes/hours
- executive/CEO: days/weeks
- quarterly financial result: current until next relevant filing/restatement
- annual revenue: current until next annual result/restatement
- registry status: jurisdiction/provider dependent
- partnership/customer count: shorter lifespan if self-reported and fast-changing

Freshness controls *research currency*, not historical correctness.

## 20. Research Coverage

Expose section/overall coverage separately from confidence.

A report with 3 perfectly verified claims and 80 missing material facts cannot claim 100% overall research confidence.

Coverage dimensions may include:
- legal identity
- financial statements
- self-reported claims
- independent verification
- management
- market/competition
- risk evidence
- recent developments
