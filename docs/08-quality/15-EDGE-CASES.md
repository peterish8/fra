# Edge Cases & Required Handling

This document is normative. The system must prefer explicit uncertainty over fabricated certainty.

## Core Rules

1. Missing evidence is not negative evidence.
2. Contradiction requires comparable, credible evidence.
3. Company-owned evidence is self-reported for underlying company claims.
4. Unknown is not zero.
5. Do not guess entity identity.
6. Do not bypass restricted access.
7. Do not manufacture precision where sources legitimately differ.

## Company / Identity

| Edge case | Required handling |
|---|---|
| No company website | Continue legal/financial/independent research; self-reported analysis `NOT_AVAILABLE`; no automatic penalty. |
| Website cannot be confirmed official | Store candidate domain as unconfirmed; verify via registry/filing/authoritative references. |
| Website down | Use previous permitted snapshot + independent sources; mark current website unavailable. |
| Company only has social media | Treat as lower-authority self-reported content if reliably official; independently verify. |
| Very new startup with sparse presence | `INSUFFICIENT_EVIDENCE`; do not assign poor trust merely for low disclosure. |
| Same company name in multiple jurisdictions | Return candidates; require strong identifier or user choice. |
| Name change/rebrand | Alias history links to same canonical legal entity when proven. |
| Parent vs subsidiary | Separate entities and `entity_scope`; never combine revenue by name similarity. |
| Merger/acquisition | Preserve pre/post relationships and effective date; historical data remains under correct entity. |
| Company dissolved | Report official current status and historical research; do not silently treat as active. |
| Delisted but still operating | Ticker becomes inactive; company entity persists. |
| Registry lookup fails | Try aliases/jurisdiction/GLEIF/OpenCorporates; if unresolved use `LEGAL_ENTITY_UNCONFIRMED`, not “fake.” |

## Access / Crawling

| Edge case | Required handling |
|---|---|
| Login required | Stop direct retrieval; use authorized/licensed alternative or mark restricted. |
| Paywall | Do not bypass; use licensed provider/other sources. |
| CAPTCHA/anti-bot block | Do not circumvent; mark `ACCESS_RESTRICTED` and fallback. |
| Robots/site policy prohibits crawl | Respect applicable restriction/provider policy; use permitted source. |
| JS-heavy public site | Use permitted browser-rendering fallback after safe URL validation. |
| Arbitrary URL points to private IP | Block through SSRF guard. |
| Redirect reaches private/restricted host | Block after re-validation. |

## Financial Data

| Edge case | Required handling |
|---|---|
| Revenue vs ARR | Different metrics; do not compare directly. |
| Gross vs net revenue | Detect definition; potential `METHODOLOGY_DIFFERENCE`. |
| GAAP vs non-GAAP | Separate accounting basis; not automatic conflict. |
| FY vs CY | Normalize/label periods; do not compare blindly. |
| Quarter vs annual | `PERIOD_MISMATCH` unless explicitly transformed. |
| USD vs INR | Preserve original currency; normalize only with explicit rate/date if needed. |
| Million vs billion | Deterministic conversion. |
| Lakh/crore | Deterministic conversion preserving original representation. |
| Rounded values differ slightly | Metric-specific tolerance. |
| `($20M)` | Parse as negative. |
| Missing value | `NULL/NOT_REPORTED`, not `0`. |
| Restatement | New fact/claim version supersedes old; history retained. |
| API vs official filing disagreement | Reconcile definition/period; filing usually canonical for filing-derived fact. |

## Claims / Evidence

| Edge case | Required handling |
|---|---|
| Claim only appears on company site | `UNVERIFIED`, not false. |
| Many sites repeat same press release | Collapse to source family; do not count as independent consensus. |
| Perplexity and Gemini cite same article | One source family. |
| Old strong source vs newer credible source | Freshness/supersession rules; retain historical truth. |
| Market-share estimates differ by methodology | Show range/uncertainty when definitions differ; no invented average. |
| Partnership logo only on company site | Unverified until partner-side/independent evidence exists. |
| Vague “backed by X” | Determine exact relationship type; do not infer investment/partnership. |
| Forecast/target | Label forecast/guidance; never historical actual. |
| Rumor/social post | Unverified report; exclude from factual verified claims unless corroborated. |
| Ongoing legal investigation | Describe investigation/allegation precisely; do not state guilt. |

## AI / Extraction

| Edge case | Required handling |
|---|---|
| Webpage contains prompt injection | Treat as untrusted content; never execute page instructions. |
| LLM returns invalid JSON | Retry bounded structured call/fallback; never accept malformed machine state. |
| LLM invents report fact | Publication mapper rejects unmatched factual sentence. |
| OCR/table extraction uncertain | Lower extraction confidence; secondary verification required for material values. |
| Non-English source | Preserve original; translate for explanation; extract numbers/dates from original when possible. |
| Ambiguous date `03/04/2026` | Resolve locale/jurisdiction/context; otherwise mark ambiguous. |

## Scores

| Edge case | Required handling |
|---|---|
| 3/3 claims verified | Do not show overall 100% if research coverage is tiny. |
| No self-reported claims | Disclosure Reliability `NOT_ENOUGH_DATA`/`NOT_APPLICABLE`, not 0. |
| Only 2 claims assessed | Do not present confident disclosure score; show provisional/insufficient sample. |
| Many trivial claims verified, one major revenue claim contradicted | Materiality weighting + prominent major contradiction. |
| Missing private-company financials | Coverage limitation, not automatic negative business score. |
| Startup 1000% growth from tiny base | Base-effect/scale adjustment. |
| Public company compared to startup | Cohort-aware scoring; do not use same raw formula. |

## Weekly Pipeline

| Edge case | Required handling |
|---|---|
| Fewer than 25 companies qualify | Publish fewer than 25; never lower evidence threshold to fill list. |
| One API down | Fallback/degraded mode; exclude candidate if critical evidence missing. |
| Cron fires twice | Same idempotency key; one staged run. |
| Worker crashes mid-run | Resume from checkpoints/retry jobs. |
| Run fails after calculating rankings | Do not replace current published watchlist; staging remains unpublished. |
| Viral PR spike | Deduplicate PR/source families and cap single-event momentum effect. |
| Rank swings weekly | Use rolling windows but allow genuine evidence-driven change. |

## Worst-Case Valid Outcome

A run may validly end as:
```text
Entity: Partially verified
Website: Not available
Financial data: Insufficient
Independent source families: 1
Claims verified: 2 / 11
Evidence coverage: 24%
Research confidence: LOW
Verdict: INSUFFICIENT EVIDENCE FOR HIGH-CONFIDENCE ANALYSIS
```

This is a successful honest system response, not a reason to hallucinate a fuller report.

