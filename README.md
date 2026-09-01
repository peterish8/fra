# Financial Research Agent — Build Specification Pack

> Working product statement: **What companies say. What the evidence says.**

This repository-style specification pack is the source of truth for building the Financial Research Agent with AI coding agents. The root contains agent instructions and project entry files; all detailed specifications live under `docs/` and are grouped by responsibility.

## Start here

1. `AGENTS.md` — mandatory repository contract for coding agents.
2. `CLAUDE.md` — Claude-specific repository guidance.
3. `GEMINI.md` — Gemini-specific repository guidance.
4. `MASTER-BUILD-PROMPT.md` — bounded first implementation prompt.
5. `docs/README.md` — complete documentation map and recommended reading order.

## GSD execution workspace

The repository now includes a GSD (Get Shit Done) planning layer under `.planning/`. It converts the specification pack into an executable OJT V1 roadmap without replacing the detailed docs.

Read these files before implementation work:

1. `.planning/PROJECT.md` — product context, constraints, decisions, and current scope.
2. `.planning/REQUIREMENTS.md` — 79 checkable V1 requirements and phase traceability.
3. `.planning/ROADMAP.md` — ten dependency-ordered phases with success criteria.
4. `.planning/STATE.md` — current execution position and blockers.
5. `.planning/phases/` — two executable plans per phase, each with tasks, dependencies, must-haves, and verification.

The intended loop is:

```text
Read source-of-truth docs → discuss the phase → plan the phase → execute bounded plans → verify → update state
```

### GSD phase map

| Phase | Focus |
|---:|---|
| 01 | Foundation & Quality |
| 02 | Workspace & Entity Resolution |
| 03 | Retrieval & Source Ledger |
| 04 | Claim & Verification Core |
| 05 | Financial Reconciliation & Conflicts |
| 06 | Durable Orchestration & Deep Verification |
| 07 | Scores & Evidence-led Report UI |
| 08 | Living Reports & Comparison |
| 09 | Weekly Watchlist & Discover |
| 10 | Hardening, Evaluation & Release |

Start implementation with Phase 01 only. Use the phase plans as execution contracts and keep the original `docs/10-planning/` files as the detailed specification/backlog source. Provider, hosting, scoring-calibration, licensing, and policy choices listed in `docs/10-planning/21-OPEN-DECISIONS.md` must be resolved explicitly before they become production behavior.

## Documentation groups

```text
docs/
├── 00-project/
│   ├── 00-STANDARDS-AND-AI-WORKFLOW.md
│   └── 01-PRD.md
├── 01-technical/
│   └── 02-TRD.md
├── 02-architecture/
│   ├── 03-ARCHITECTURE-HLD.md
│   └── adr/
├── 03-data/
│   ├── 04-DATABASE-SCHEMA.md
│   └── schema.sql
├── 04-api/
│   ├── 05-API-SPEC.md
│   └── openapi.yaml
├── 05-research-engine/
│   ├── 06-RESEARCH-VERIFICATION-SPEC.md
│   ├── 07-SCORING-RANKING-SPEC.md
│   ├── 08-PROVIDER-ROUTING-FALLBACKS.md
│   └── 20-LLM-CONTRACTS.md
├── 06-product-design/
│   ├── 09-UI-UX-SPEC.md
│   └── 10-DESIGN-SYSTEM.md
├── 07-security-governance/
│   ├── 11-SECURITY-THREAT-MODEL.md
│   └── 16-DATA-GOVERNANCE-LEGAL.md
├── 08-quality/
│   ├── 12-TESTING-EVALUATION.md
│   ├── 15-EDGE-CASES.md
│   └── 19-DEFINITION-OF-DONE.md
├── 09-operations/
│   ├── 13-OBSERVABILITY-OPERATIONS.md
│   └── 14-DEPLOYMENT-CI-CD.md
└── 10-planning/
    ├── 17-IMPLEMENTATION-PLAN.md
    ├── 18-TASK-BACKLOG.md
    └── 21-OPEN-DECISIONS.md
```

## Development method

Use **Spec → Plan → Tasks → Implement → Verify**. Do not let an implementation agent invent behavior that conflicts with the specifications. If requirements change, update the relevant document or ADR first, then code and tests.

## Target architecture

- **Frontend:** Next.js + TypeScript + Tailwind CSS + shadcn/ui + Recharts.
- **Backend:** Python + FastAPI + Pydantic, modular monolith.
- **Database/Auth:** Supabase PostgreSQL + Supabase Auth + RLS.
- **Background jobs:** durable Postgres-backed research jobs/workers for V1.
- **Primary research:** Perplexity Search API.
- **Independent deep research:** Gemini Deep Research API.
- **Extraction:** Firecrawl → Exa Contents → permitted browser-rendering fallback.
- **Government/legal verification:** country registry adapters, GLEIF, OpenCorporates fallback.
- **Financial data:** official filings/XBRL first, commercial financial APIs for cross-check/fallback.
- **Hosting:** Vercel frontend + persistent Python API/worker host + Supabase.
- **No MCP in product scope.** Integrations are server-side provider adapters.

## Non-negotiable product rules

- Company-owned content is **self-reported evidence**, not independent confirmation.
- Missing evidence is not negative evidence.
- `UNVERIFIED` and `CONTRADICTED` are different states.
- No factual claim enters a `VERIFIED` report without supporting evidence and a verification record.
- Numerical derivations are deterministic where possible.
- Provider agreement is not source independence; shared root sources count as one source family.
- Never bypass login, CAPTCHA, paywalls, private APIs, or access controls.
- The Top 25 is a **Research Watchlist**, not an investment recommendation.
- Report updates are versioned and do not silently overwrite prior research.
