# Open Decisions / Do Not Guess

Coding agents must not silently decide these items. Use sensible scaffolding/interfaces, but require an explicit product/ADR decision before locking production behavior.

## Product

- Final product/brand name. Current documents use “Financial Research Agent.”
- Whether public sharing/export is included in OJT V1.
- Exact initial countries beyond US + India/UK demonstration coverage.
- Whether weekly watchlist shows one combined ranked list, separate public/private tabs, or both. Cohort-aware scoring is mandatory regardless.

## Providers

- Final commercial financial-data provider after benchmark (EODHD vs Twelve Data vs alternatives).
- Exact browser-rendering fallback after pricing/reliability test.
- Whether Brave/Exa/Tavily are all enabled or only one fallback.
- Whether Crunchbase/Dealroom licensing is affordable/allowed for weekly startup discovery.
- Primary LLM provider/model for extraction, semantic verification and synthesis.
- Whether a second LLM adjudicator is needed after evaluation.

## Infrastructure

- Exact persistent Python host (Railway/Render/Fly/other).
- Whether Postgres-backed queue remains sufficient after load tests or Redis/managed queue is justified.
- Source full-text storage location/retention based on provider/source licensing.

## Scoring

- Final calibrated weights/thresholds after labeled evaluation.
- Sector-specific scorecards required for first release.
- Minimum sample/coverage threshold for Disclosure Reliability after testing.
- Weekly ranking rolling-window lengths and event caps.

## UX

- Final brand palette/logo.
- Whether dark mode is in V1.
- Exact mobile scope for complex comparison/report tables.

## Policy

- Final Terms/Privacy language.
- Commercial/public display rights for each provider/source category.
- Public-report attribution requirements.

## Rule

If implementation needs one of these decisions, create a small proposal with options/trade-offs and ask for/record the decision. Do not invent it inside a code change.
