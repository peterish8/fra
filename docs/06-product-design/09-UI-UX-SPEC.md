# UI/UX Specification

## 1. Product UX Goal

The interface should feel like a **research workspace**, not a chat wrapper. Users should be able to scan a report quickly, then drill into the exact evidence behind any claim.

Core experience:
```text
Discover / Search
  -> Create or open report workspace
  -> Watch research progress
  -> Read current report
  -> Inspect claim evidence/conflicts
  -> Refresh later
  -> Compare versions
```

## 2. Information Architecture

### Global navigation
- **Discover** — weekly watchlist and recent public research.
- **My Research** — persistent personal reports.
- **Compare** — multi-company comparison.
- **Settings** — account, plan/quotas, provider-independent user preferences.

### Left sidebar
ChatGPT-like persistence, but each item is a research workspace:
```text
MY RESEARCH
NVIDIA — Deep Research
AMD — Risk Analysis
Apple — Financial Health
NVIDIA vs AMD

WEEKLY
Week 35 Research Watchlist
Week 34 Research Watchlist
```

Sidebar requirements:
- search
- recent/favorites
- company favicon/logo only when verified/sourced
- last updated
- status indicator
- collapsible on desktop; drawer on mobile

## 3. Core Screens

### 3.1 Discover / Home
Hero:
- product statement
- prominent company research input
- research depth/focus progressive disclosure

Below:
- latest Top 25 Research Watchlist
- methodology version + update timestamp
- filter by public/private/startup/sector/country
- ranked cards/table with score breakdown preview, confidence/coverage and rank change

Never headline “best stocks to buy.” Use “Research Watchlist,” “Evidence-backed momentum,” or similar non-advice wording.

### 3.2 Create Research
Input options:
- company name/ticker/domain
- jurisdiction optional
- research focus chips
- depth: Fast / Standard / Deep
- optional comparison company

After submit, resolve entity. If ambiguous, show candidate selector before expensive research.

### 3.3 Research Progress
Avoid fake percentage precision. Show deterministic stage progress:
```text
✓ Entity resolved
✓ Registry checked
✓ Company claims captured
● Independent research in progress
○ Financial cross-check
○ Verification
○ Report synthesis
```

Show useful counters:
- sources found
- independent source families
- claims extracted
- claims verified
- conflicts found
- follow-up searches

If provider degraded, show subtle note without exposing internal secrets.

### 3.4 Report Workspace
Header:
- company/legal name
- ticker/country/entity type
- last verified timestamp
- current version
- Refresh button
- Compare button
- Export optional

Top quality cards, always distinct:
- **Research Confidence**
- **Evidence Coverage**
- **Disclosure Reliability** (or `Not enough data`)
- **Financial/Business Score** if applicable

Do not combine into one trust score.

Tabs/sections:
1. Overview
2. Claims vs Evidence
3. Financials
4. Growth / Traction
5. Risks
6. Recent Developments
7. Competition
8. Conflicts
9. Sources
10. History

### 3.5 Claims vs Evidence
Primary differentiated screen.

Table columns:
- Claim
- Origin (`Self-reported`, `Independent`, `Derived`)
- Materiality
- Verdict
- Confidence
- Independent source families
- Freshness
- Evidence action

Filters:
- All
- Verified
- Partial
- Contradicted
- Unverified
- Stale
- Self-reported only
- High/Critical materiality

### 3.6 Claim Inspector Drawer
Open from any factual claim.

Sections:
- exact claim
- claim origin
- structured value/period/entity scope
- verdict + confidence
- **What the company said** if applicable
- **What independent evidence says**
- supporting evidence excerpts
- contradicting evidence excerpts
- source authority/type/family
- numeric check
- temporal check
- adversarial check
- conflicts
- confidence breakdown
- version history

The drawer must make “why did the system say this?” answerable without reading logs.

### 3.7 Financials
Use tables first, charts second.

Each metric row/cell has evidence affordance.
Display:
- original reported value
- normalized value only when helpful
- period
- source
- verification status

Charts may show revenue/profit/margins over time, but clicking a datapoint should reveal source/period.

### 3.8 Conflicts
Group by conflict severity.

Card example:
```text
Revenue FY2025
Company statement: $25M
Registry/filing: $18.7M
Financial API: $18.9M

Status: Genuine value conflict
Possible explanation checked: period ✓ currency ✓ scope ✓
```

Use precise wording such as “Contradicted by current evidence,” not “Company is lying.”

### 3.9 History / Diff
Timeline:
```text
v1 Aug 31 — Initial research
v2 Sep 18 — Earnings update
v3 Nov 22 — New filing
```

Diff summary:
- added
- updated
- invalidated
- became stale
- new conflicts
- resolved conflicts
- score changes

Changed claim view shows before/after evidence and change reason.

### 3.10 Comparison
Normalized comparison table by cohort-compatible metrics.
Each cell opens claim evidence.
Do not show “N/A” as zero.

## 4. Empty/Error States

### No website
```text
Official website: Not found / not confirmed
Self-reported claim analysis: Not available
Independent/legal research: continuing
```
No score penalty solely for missing website.

### Insufficient evidence
Make this a first-class successful result:
```text
Research confidence: Low
Evidence coverage: 24%
We could not gather enough independent evidence for a high-confidence conclusion.
```

### Ambiguous entity
Require user selection; do not guess.

### Provider outage
Show “Research completed with reduced provider coverage” and list affected evidence categories, not provider secrets.

## 5. UX Writing Rules

Prefer:
- “Independently verified”
- “Unverified”
- “Contradicted by current evidence”
- “Possible period mismatch”
- “Insufficient evidence”
- “Disclosure reliability”

Avoid:
- “This company is truthful/untruthful”
- “Safe investment”
- “Guaranteed”
- “Fraud” unless reporting an authoritative legal finding with evidence
- fake precision

## 6. Accessibility

- WCAG AA target.
- Keyboard navigable tables/drawers.
- Visible focus states.
- Status icon + text, never color only.
- Tooltips cannot be the only way to access critical explanations.
- Tables need responsive alternatives on mobile.
- Charts need textual/tabular equivalents.

## 7. Responsive Strategy

Desktop is primary for dense research, but mobile supports:
- report reading
- claim inspector
- watchlist browsing
- refresh status

On mobile, tables become stacked metric/claim rows rather than horizontal overflow where possible.

## 8. Performance UX

- Skeletons only for known layout.
- Lazy-load deep evidence panels.
- Paginate/virtualize large claim/source lists.
- Preserve scroll/tab state when opening/closing evidence drawer.
- Optimistic UI only for safe local actions (favorite/title), not research completion/verdict changes.

