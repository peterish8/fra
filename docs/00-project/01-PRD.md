# Product Requirements Document (PRD)

## Product Goal

Create a company-intelligence and financial-research workspace that separates **what a company says about itself** from **what independent evidence can actually verify**.

The product will collect self-reported company claims, independently cross-check them using government/company registries, regulatory filings, structured financial APIs, web research, and deep-research providers, then produce evidence-backed living reports with claim-level verdicts, confidence, disclosure reliability, source conflicts, and version history.

A scheduled weekly research pipeline will also publish a **Top 25 Research Watchlist** based on transparent, evidence-backed scoring. The watchlist is discovery/research tooling, not investment advice.

## Target Users

- Financial analysts and researchers
- Investors doing preliminary company research
- Students/researchers studying companies
- Founders/operators researching competitors
- Due-diligence teams needing traceable evidence

## Product Principles

- Evidence before explanation.
- Self-reported company content is a claim source, not independent truth.
- Missing evidence is not negative evidence.
- `UNVERIFIED` is not `CONTRADICTED`.
- Every important factual claim must be traceable to evidence.
- No unsupported financial claims in a verified report.
- Sources provide facts; deterministic code calculates derived numbers; LLMs assist with extraction, reasoning, and synthesis.
- Conflicts are surfaced and explained, not silently averaged away.
- Confidence must be explainable and decomposable.
- Research history is versioned and never silently overwritten.
- The system must know when it does not have enough evidence.
- Provider/model agreement does not equal source independence.
- Public crawling must respect access controls and source policies.
- The product does not label companies as fraudulent or dishonest without authoritative evidence; it reports claim/evidence status precisely.

## Feature Priorities

| Feature | Priority |
|---|---|
| User authentication | Must |
| Research report/workspace creation | Must |
| Company/entity resolution | Must |
| Country/jurisdiction legal-registry verification | Must |
| Public company-website claim extraction | Must |
| Multi-source independent retrieval | Must |
| Structured financial-data retrieval | Must |
| Official filing/document retrieval | Must |
| Structured fact/number extraction | Must |
| Atomic claim generation | Must |
| Claim-to-evidence mapping | Must |
| Automated citation verification | Must |
| Deterministic numeric validation | Must |
| Period/currency/unit normalization | Must |
| Source-independence/deduplication detection | Must |
| Conflicting-source detection | Must |
| Explainable claim confidence | Must |
| Automatic follow-up research | Must |
| Basic and deep report generation | Must |
| Persistent Truth Ledger / audit trail | Must |
| Research run progress/status | Must |
| Report library/sidebar | Must |
| Report version history | Must |
| Multi-company comparison | Must |
| Adversarial claim verification | Should |
| Conflict classification/resolution | Should |
| Evidence freshness tracking | Should |
| Living report refresh | Should |
| Report version diff | Should |
| Disclosure Reliability score | Should |
| Research Confidence score | Should |
| Source DNA / authority classification | Should |
| Weekly Top 25 Research Watchlist | Should |
| Scheduled weekly refresh pipeline | Should |
| Claim inspector/evidence drawer | Should |
| PDF/export/share | Could |
| Notifications for changed/stale reports | Could |
| Additional country registry adapters | Could |

## User Stories

### US-001 — Create Research Workspace
As a researcher, I want to create a research workspace so that I can investigate a company or comparison topic over time.

**Acceptance criteria**
- Unique `report_id` generated.
- User can enter company name/ticker/domain or comparison request.
- User can choose focus: financials, growth, risks, recent developments, competition, disclosure verification, or full research.
- Report status begins as `DRAFT`.

### US-002 — Resolve the Correct Company
As a researcher, I want the system to identify the correct legal entity so that evidence from similarly named companies is not mixed.

**Acceptance criteria**
- Resolve canonical company identity using name, country, ticker, registration identifiers, domain and aliases.
- If identity confidence is below threshold, ask the user to choose among candidates.
- Store aliases, former names and parent/subsidiary relationships separately.
- Research cannot receive a high-confidence legal-identity status until entity resolution succeeds.

### US-003 — Verify Legal/Registry Information
As a researcher, I want legal company information checked against official sources so that I know the company entity actually exists and which jurisdiction governs it.

**Acceptance criteria**
- Route verification to the appropriate country adapter when available.
- Store legal name, registration identifier, status, jurisdiction, retrieved-at timestamp and source.
- Official source freshness is recorded; stale registry data is not treated as current by default.
- Failure to locate a company returns `LEGAL_ENTITY_UNCONFIRMED`, not “fake company.”

### US-004 — Capture Self-Reported Company Claims
As a researcher, I want the company’s own public statements extracted so that I can compare what it says with independent evidence.

**Acceptance criteria**
- Crawl only publicly accessible permitted pages.
- Store extracted statements as `SELF_REPORTED` claims.
- Preserve exact source URL, page snapshot/hash, retrieval time and evidence excerpt.
- Company-owned pages cannot independently verify company-owned claims.
- If no website exists, research continues and self-reported coverage is `NOT_AVAILABLE`.

### US-005 — Retrieve Independent Sources
As a researcher, I want multiple independent sources so that research is not based on one provider or one article.

**Acceptance criteria**
- Use configured search/research providers and official sources.
- Company-owned domains are excluded from independent-verification searches for self-reported claims.
- Duplicate/syndicated sources are grouped into a source family.
- Search provider agreement is not counted as independent confirmation if providers cite the same underlying source.

### US-006 — Extract Structured Financial Facts
As a researcher, I want financial facts normalized into structured values so that numbers can be checked and compared.

**Acceptance criteria**
- Store metric, value, unit, currency, company/entity scope, period, accounting basis and source.
- Preserve original representation alongside normalized representation.
- Support million/billion, lakh/crore, percentages, negative accounting notation and common financial periods.
- `NULL/unknown` is never converted to numerical zero.

### US-007 — Verify Every Important Claim
As a researcher, I want every important claim tied to evidence so that I can inspect exactly why the system believes it.

**Acceptance criteria**
- Important factual report statements are represented as atomic claim objects.
- Every cited claim links to one or more evidence records.
- Semantic verification returns `SUPPORTED`, `PARTIAL`, `UNSUPPORTED`, or `INSUFFICIENT` internally.
- A report cannot be marked `VERIFIED` unless all required citation-bearing claims have verification records.
- OJT target: 100% citation-verification coverage for published verified reports.

### US-008 — Validate Financial Numbers Deterministically
As a researcher, I want numerical claims checked using code so that unit conversions and derived metrics do not rely on LLM intuition.

**Acceptance criteria**
- Currency, units, signs, periods and formulas are validated by deterministic Python functions where possible.
- YoY growth, margin and ratio calculations store their calculation inputs and formula version.
- Tolerances are metric-specific and explicit.
- Numeric mismatch is visible in the claim inspector.

### US-009 — Detect and Explain Conflicts
As a researcher, I want disagreements between sources flagged so that uncertainty is visible.

**Acceptance criteria**
- Compare like-for-like facts only after metric, period, currency and entity-scope normalization.
- Classify conflicts such as `VALUE_CONFLICT`, `PERIOD_MISMATCH`, `CURRENCY_MISMATCH`, `METHODOLOGY_DIFFERENCE`, `GAAP_VS_NON_GAAP`, `ENTITY_SCOPE_DIFFERENCE`, `SOURCE_DATE_MISMATCH`, `RESTATEMENT`.
- Genuine unresolved conflicts remain visible.
- OJT target: 90%+ correct disagreement detection on evaluation cases.

### US-010 — Follow Up When Evidence Is Weak
As a researcher, I want the agent to perform additional research when evidence is insufficient or conflicting.

**Acceptance criteria**
- Weak/high-materiality claims can trigger new search queries.
- New evidence attaches to the existing claim lineage.
- Verification reruns after follow-up research.
- Maximum retry/loop budget is enforced.
- If evidence remains insufficient, output remains `UNVERIFIED`/`INSUFFICIENT_EVIDENCE`.

### US-011 — Challenge Important Claims
As a researcher, I want important claims actively challenged so that the system does not only search for confirming information.

**Acceptance criteria**
- High-materiality claims may trigger adversarial search prompts.
- Counterevidence and alternative definitions are stored.
- Claim wording may be weakened if stronger wording is not supported.
- Adversarial outcome contributes to explainable confidence.

### US-012 — Understand Claim Confidence
As a researcher, I want an explainable confidence score so that I can understand evidence quality rather than receive an arbitrary AI percentage.

**Acceptance criteria**
- Score is deterministic/config-driven and versioned.
- Components can include support quality, source authority, independence, numeric validation, temporal alignment, freshness, source agreement and adversarial survival.
- `N/A` dimensions are re-normalized rather than treated as failures.
- Material unresolved contradictions can cap confidence regardless of average score.

### US-013 — Understand Disclosure Reliability
As a researcher, I want to see how often material company-made claims survive independent verification.

**Acceptance criteria**
- Score uses only eligible self-reported claims.
- Show counts/weights for verified, partial, contradicted and unverified claims.
- Show independent-verification coverage separately from reliability.
- If sample size/coverage is too low, display `NOT_ENOUGH_DATA`, not a misleading numeric score.
- Never label the metric simply “company trustworthiness.”

### US-014 — Read a Beautiful Evidence-Backed Report
As a researcher, I want a readable research report so that complex evidence can be understood quickly.

**Acceptance criteria**
- Report includes executive summary, identity/legal status, financials, growth, risks, recent developments, competition, claims-vs-evidence, conflicts, source quality and limitations.
- Every factual statement in verified sections maps back to claim IDs.
- Important scores have a drill-down explanation.
- Confidence/status is not communicated by color alone.

### US-015 — Inspect Evidence
As a researcher, I want to click a claim and see the evidence so that I can audit the system.

**Acceptance criteria**
- Claim inspector shows claim, origin, exact excerpts, URLs/doc references, source authority, source family, numeric/period checks, conflicts, adversarial result, confidence explanation and history.
- Original source context is accessible where legally/permissibly available.

### US-016 — Save and Revisit Reports
As a researcher, I want reports saved in a sidebar/library so that research is persistent like a workspace rather than a one-time response.

**Acceptance criteria**
- Search/filter reports by title/company/status/date.
- Opening a report restores current version and history.
- Multiple reports can exist for the same company with different research goals.

### US-017 — Update a Living Report
As a researcher, I want to refresh an existing report so that I can keep the same workspace current.

**Acceptance criteria**
- Refresh creates a new research run and new report version.
- Previous versions remain immutable/readable.
- System can prioritize stale/affected claims instead of always recomputing everything.
- New findings update the Truth Ledger before the report view.

### US-018 — Compare Versions
As a researcher, I want to see what changed since the previous research run.

**Acceptance criteria**
- Show unchanged, updated, added, invalidated and newly conflicted claims.
- Changed claims show old/new value, evidence and reason for change.

### US-019 — Compare Companies
As a researcher, I want normalized company comparisons so that I can compare the same metrics without losing evidence provenance.

**Acceptance criteria**
- Comparison supports at least two companies.
- Cells link to evidence/claim records.
- Incompatible metrics are not compared as if identical.
- Public/private/startup differences are clearly labeled.

### US-020 — Weekly Top 25 Research Watchlist
As a user, I want a refreshed weekly list of research-worthy companies so that I can discover companies with strong evidence-backed momentum.

**Acceptance criteria**
- Scheduled discovery runs weekly.
- Uses a cost-aware funnel: broad discovery → cheap screening → verified shortlist → deep research finalists.
- Companies must meet minimum entity/evidence coverage to be eligible.
- Ranking methodology and score components are visible.
- Public companies and startups/private companies use cohort/stage-aware scoring.
- System may publish fewer than 25 if fewer candidates meet quality thresholds.
- Watchlist explicitly states it is research discovery, not investment advice.

## Product States

### Research run
`QUEUED → PLANNING → ENTITY_RESOLUTION → RETRIEVING → EXTRACTING → VERIFYING → RESOLVING_CONFLICTS → FOLLOW_UP_RESEARCH → SCORING → SYNTHESIZING → READY`

Failure/terminal alternatives: `PARTIAL`, `FAILED`, `CANCELLED`.

### Report
`DRAFT → RESEARCHING → READY → VERIFIED`

A report may remain `READY` without becoming `VERIFIED` if publication gates are not satisfied.

### Claim verdict
`UNVERIFIED → VERIFIED | PARTIALLY_SUPPORTED | CONTRADICTED | INSUFFICIENT_EVIDENCE | STALE`

### Evidence freshness
`CURRENT → AGING → STALE → INVALIDATED`

### Provider call
`PENDING → SUCCESS | NO_RESULTS | RATE_LIMITED | ACCESS_RESTRICTED | PARSE_FAILED | TEMPORARY_FAILURE | PERMANENT_FAILURE`

## Out of Scope for V1

- Executing trades or brokerage integration.
- Personalized investment recommendations.
- Automated fraud accusations or legal judgments.
- Bypassing authenticated/restricted website access.
- Full global registry coverage on day one.
- Microservice architecture.
- Vector database unless a measured retrieval need justifies it.
- Social-media scraping requiring prohibited/private access.
- MCP/plugin interface.

## Success Metrics

### Required OJT metrics
- 100% of citations in verified reports have automated verification records.
- 90%+ correct conflicting-source flagging on the curated evaluation set.

### Product quality metrics
- Unsupported-claim rate in `VERIFIED` reports: <1% on evaluation set.
- Numeric normalization/calculation accuracy: >=99% on deterministic test set.
- Entity-resolution precision: >=98% on supported jurisdictions with sufficient identifiers.
- Source-family duplicate detection precision: >=95% on test set.
- Research-run completion without manual recovery: >=95% excluding provider-wide outages.
- Every published score exposes score version and component breakdown.
- Every report version is reproducible from stored run metadata/source snapshots where licenses permit.

