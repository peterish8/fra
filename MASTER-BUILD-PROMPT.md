# Master Build Prompt for a Coding Agent

Build the Financial Research Agent described in this repository. Do **not** attempt to build the whole application in one unreviewed pass.

## Mandatory onboarding

1. Read `AGENTS.md`.
2. Read `README.md`.
3. Read `docs/00-project/01-PRD.md`, `docs/01-technical/02-TRD.md`, `docs/02-architecture/03-ARCHITECTURE-HLD.md`.
4. Read `docs/10-planning/17-IMPLEMENTATION-PLAN.md`, `docs/10-planning/18-TASK-BACKLOG.md`, and `docs/08-quality/19-DEFINITION-OF-DONE.md`.
5. For each implementation task, load only the relevant domain/UI/security specs referenced by `AGENTS.md`.

## First assignment

Start with **Phase 0 only** from `docs/10-planning/17-IMPLEMENTATION-PLAN.md`:
- create the frontend/backend repository structure
- Next.js TypeScript/Tailwind/shadcn setup
- FastAPI/Pydantic setup
- Supabase integration scaffolding
- typed configuration using `.env.example`
- baseline database migrations from `docs/03-data/schema.sql` (adapt safely to migration tooling)
- structured logging/request IDs
- health endpoints
- GitHub Actions quality checks
- minimal authenticated shell/report-list placeholder

## Workflow

Before editing code:
1. inspect the current repository state
2. produce a concise implementation plan mapped to task IDs
3. identify assumptions or spec conflicts
4. do not invent providers/business logic not yet needed

During implementation:
- keep a modular monolith
- write tests for deterministic/domain behavior
- keep provider keys server-side
- do not add MCP
- do not implement any access-control bypass/crawler evasion
- do not make report prose the canonical data model

Before completion:
- run lint/typecheck/tests/build/migration validation
- fix failures
- summarize files changed, tests run, remaining task IDs and any spec decisions needed
- do not claim success without command evidence

After Phase 0 is verified, proceed one bounded phase/task group at a time, using the acceptance criteria and Definition of Done.

