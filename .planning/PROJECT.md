# Financial Research Agent

## What This Is

Financial Research Agent is an evidence-first company-intelligence workspace for analysts, researchers, investors doing preliminary research, operators, students, and due-diligence teams. It captures what a company says about itself, gathers permitted public and official evidence, and produces versioned reports whose claims, sources, conflicts, calculations, and uncertainty can be inspected.

The repository currently contains the build specification pack rather than an application implementation. This planning workspace turns that specification into an executable GSD roadmap for the first OJT release.

## Core Value

Every important report statement must let a researcher see what was claimed, what evidence supports or contradicts it, and how confident the system should be.

## Requirements

### Validated

None yet. This is a greenfield implementation plan; the source-of-truth docs are requirements, not shipped behavior.

### Active

- [ ] Authenticated users can create, revisit, refresh, compare, and inspect persistent company research workspaces.
- [ ] Company identity and jurisdiction are resolved conservatively, with ambiguity surfaced rather than guessed.
- [ ] Public company statements are classified as self-reported and independently checked against permitted source families.
- [ ] Facts, atomic claims, evidence, verification records, conflicts, scores, and report versions persist in PostgreSQL as the Truth Ledger.
- [ ] Financial values are normalized and derived deterministically where possible; mismatches remain explainable.
- [ ] Long-running research is durable, resumable, idempotent, budget-aware, and observable.
- [ ] Reports expose separate, explainable confidence/coverage/disclosure/business scores rather than one trust score.
- [ ] Users can read reports, inspect evidence, understand conflicts, compare companies/versions, and browse the weekly Research Watchlist.
- [ ] Security, evaluation, accessibility, deployment, and release gates are demonstrated with fixtures and tests.

### Out of Scope

- Executing trades, brokerage integrations, or personalized investment recommendations — the watchlist is research discovery, not advice.
- Fraud accusations, legal judgments, or moral labels inferred from data mismatches — the product reports evidence status precisely.
- Login/paywall/CAPTCHA/anti-bot bypasses, private endpoints, prohibited scraping, or social-media access requiring restricted access.
- Microservices, a vector database, an event bus, or an MCP/plugin layer in V1 — the accepted ADRs favor a modular monolith and PostgreSQL-first design.
- Full global registry coverage on day one — start with configured US plus one India/UK demonstration route and extensible adapters.
- PDF/export/share, notifications, and additional country adapters until the OJT release has validated the core pipeline.

## Context

- Canonical source documents live under `docs/`; `AGENTS.md` is the repository contract.
- Existing planning in `docs/10-planning/17-IMPLEMENTATION-PLAN.md` defines ten logical steps (Phase 0 through Phase 9). This roadmap renumbers them 01 through 10 for GSD conventions while preserving their dependency order.
- Target stack: Next.js/TypeScript/Tailwind/shadcn/Recharts; FastAPI/Python/Pydantic; Supabase PostgreSQL/Auth/RLS; durable Postgres-backed workers; Vercel plus a persistent Python host.
- Reports are projections over immutable/versioned ledger records. Provider responses are normalized behind adapters, and all retrieved content is untrusted evidence.
- The source pack has unresolved choices around provider vendors, hosting, scoring calibration, public sharing, country coverage, retention/licensing, and final legal language. Plans must scaffold interfaces and record proposals rather than silently deciding these.

## Constraints

- **Truth semantics**: Missing evidence is not negative evidence; `UNVERIFIED`, `CONTRADICTED`, and `INSUFFICIENT_EVIDENCE` remain distinct.
- **Architecture**: Keep a modular monolith; business logic belongs in domain/services, not route handlers or React components.
- **Durability**: Research state, audit data, and report lineage live in PostgreSQL; jobs must checkpoint and resume safely.
- **Provider safety**: Secrets stay server-side, provider calls use contracts/fallbacks, and public retrieval stops at access restrictions.
- **Numerical correctness**: Normalize units/periods/currencies and calculate derivations in deterministic code, not LLM prose.
- **Quality**: A verified report requires 100% citation-verification coverage and no hidden critical conflict; CI must cover frontend, backend, schema, API, security, and evaluation checks.
- **UX**: Dense financial information stays readable; uncertainty, status, and score explanations cannot depend on color alone.
- **Planning**: Each phase is independently verifiable and each plan is bounded to roughly 2–3 implementation tasks.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use the existing ten-step implementation order as the GSD phase backbone | It already encodes dependency order from foundation through evaluation | ✓ Good |
| Use ten numbered GSD phases with two plans each | Medium/fine granularity gives implementers bounded vertical slices without exploding the roadmap | — Pending |
| Treat the docs pack as the current truth source | There is no implementation yet and no Git history to prefer | — Pending |
| Keep open provider, hosting, scoring, UX, and policy choices as explicit decisions | The source pack says agents must not guess these | — Pending |

---
*Last updated: 2026-09-01 after initial GSD planning from the complete specification pack*
