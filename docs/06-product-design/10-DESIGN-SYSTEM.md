# Design System

## 1. Visual Direction

Editorial financial research desk + modern developer-tool clarity.

Keywords:
- precise
- calm
- evidence-first
- dense but not cramped
- editorial report readability
- compact coverage rail
- minimal chrome

Reference interaction pattern: a researcher should see their coverage context,
choose a research mode, identify a company/ticker, state a brief, and open a
workspace in one contained composition. The page should read like an analyst
desk, not a trading terminal or generic SaaS dashboard.

Avoid:
- decorative gradients
- glow-heavy surfaces
- excessive card nesting
- decorative 3D
- hover scaling
- stock-market casino aesthetics

Restrained glass is permitted only for contextual chrome: the navigation rail,
application header, and a primary command surface may use a low-opacity fill,
subtle border highlight, and `backdrop-filter` blur over a stable dark canvas.
Do not apply glass treatment to evidence tables, claims, source text, or any
surface where translucency would reduce legibility. Each glass surface needs a
solid fallback, a visible focus state, and contrast sufficient for both text
and interactive controls.

## 2. Typography

Recommended:
- UI/body: refined humanist sans such as **Avenir Next** or equivalent
- display/report headings: a restrained editorial serif such as **Instrument
  Serif** or a close system fallback
- numeric/tabular data and tickers: enable tabular numerals with **IBM Plex
  Mono** or equivalent

Hierarchy:
- page title: 28–32px desktop
- section title: 20–24px
- card metric: 24–30px
- body: 14–16px
- evidence metadata: 12–13px, never below accessible readability

Use sentence case. Use mono uppercase sparingly for tickers and tiny metadata
labels; do not use it as a substitute for hierarchy.

## 3. Color Tokens

Use semantic tokens rather than hard-coded component colors.

Suggested light theme:
```text
--bg: #F7F8FA
--surface: #FFFFFF
--surface-subtle: #F1F3F6
--border: #E2E6EC
--text: #111827
--text-muted: #667085
--accent: #5B5BD6
--accent-soft: #EEEEFF

--success: #18864B
--warning: #A66300
--danger: #B42318
--info: #2563EB
```

Status colors are supportive only; always show label/icon/text.

Dark mode can follow later using token inversion; do not duplicate component logic.

## 4. Spacing & Layout

- 4px base spacing system.
- Main report reading width ~760–900px; evidence/detail workspace can use wider split layout.
- Sidebar ~260px desktop.
- Header/actions remain compact.
- Use generous vertical separation between report sections, tighter spacing inside data tables.

## 5. Surfaces

Use three elevation levels:
1. page background
2. primary surface/card
3. overlay/drawer/popover

Prefer 1px borders and subtle shadow only for overlays. Avoid every section becoming a boxed card.

## 6. Components

Core reusable components:
- `AppSidebar`
- `ResearchCommandBar`
- `ResearchProgressTimeline`
- `QualityMetricCard`
- `VerdictBadge`
- `MaterialityBadge`
- `EvidenceCoverageBar`
- `ClaimTable`
- `ClaimInspectorDrawer`
- `SourceChip`
- `SourceAuthorityLabel`
- `ConflictCard`
- `FinancialMetricTable`
- `EvidenceLinkedChart`
- `ReportVersionTimeline`
- `DiffSummary`
- `WatchlistTable`
- `RankDelta`
- `EmptyEvidenceState`

Use shadcn primitives where suitable but build domain components above them.

## 7. Status Semantics

Verdict presentation:
- Verified: check icon + “Verified”
- Partial: half/alert icon + “Partially supported”
- Contradicted: X/alert icon + “Contradicted”
- Unverified: question icon + “Unverified”
- Insufficient: info icon + “Insufficient evidence”
- Stale: clock icon + “Stale”

Never use “red = bad company.” Red indicates a specific evidence problem, not moral judgment.

## 8. Tables

- Sticky header for long lists.
- Right-align numeric values.
- Tabular numerals.
- Keep units visible.
- Do not hide period/currency in hover-only UI.
- User can open evidence from any material numeric cell.
- Sort/filter affordances must be obvious.

## 9. Charts

Only use charts when they answer a question better than a table.

Rules:
- no 3D
- no dual y-axis unless unavoidable and clearly explained
- source-linked datapoints
- show missing data as missing, not zero
- distinguish actual vs estimate/forecast
- show period granularity clearly

## 10. Motion

Use motion for orientation only:
- drawer open/close
- stage progress transition
- diff highlight fade

150–220ms typical. Respect reduced-motion preferences.

## 11. Design QA Checklist

Before approving a screen:
- Can user tell what is verified vs merely reported?
- Can user find evidence in <=2 interactions?
- Are uncertainty and missing data explicit?
- Is there any score without an explanation path?
- Does mobile preserve the core meaning?
- Does keyboard navigation work?
- Is status readable without color?
- Are dense tables still scannable?
