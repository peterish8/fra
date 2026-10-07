# Product audit (2026-10-07)

## Summary

The backend test suite passes (392 tests in about 2 seconds), but nothing in
it touches a real database, search provider or language model. The
specification is strong; the running product is a demo. `STATE.md` reports
"Phase 10 of 10, 100%", which measures plans and fixtures, not a working
product.

## Part 1: Problems in the product and the code

### Blockers: the core product does not exist yet

1. **No language model is ever called.** `backend/app/providers/llm/` holds
   schemas only. `providers/research/adapters.py` states that it "performs
   no live provider calls", and its `research()` returns an empty result.
   Perplexity, Gemini, Firecrawl, Exa and Brave have settings but no client
   code. Claim extraction, verification and report writing are not built.
2. **No database.** Every repository is an in-memory dict
   (`InMemoryClaimRepository`, `InMemoryResearchRunRepository`, and so on).
   No Postgres driver is a dependency, and `persistence/migration.py` only
   reads SQL files as text. A restart loses every report.
3. **The frontend runs on demo data.** `/research`, `/reports`, `/compare`,
   `/admin` and `/tearsheet` import `lib/demo-data.ts` and
   `lib/demo-api-client.ts`. Apart from the News tab, the UI never calls the
   backend.
4. **Deployment is broken.** `deploy/docker-compose.yml` builds `../backend`,
   but there is no `Dockerfile`, and it runs `python -m app.jobs.worker`, a
   module that does not exist.
5. **The API will not start without fake keys.** `config/settings.py`
   requires `PERPLEXITY_API_KEY`, `EXA_API_KEY`, `FIRECRAWL_API_KEY`,
   `GEMINI_API_KEY`, `LLM_API_KEY` and others that no code uses.

### Security and correctness

6. **Login checks will break on newer Supabase projects.**
   `security/auth.py` accepts only HS256 tokens signed with a shared secret.
   Newer Supabase projects sign with asymmetric keys; verify against
   Supabase's published JWKS instead.
7. **Audience is not checked.** `verify_aud: False` is hard-coded although a
   `supabase_jwt_audience` setting exists.
8. **Admin access reads the token's `role` claim.** Supabase sets it to
   `authenticated` for everyone, so no real user can become admin. Store
   admin rights in a table or in `app_metadata`.
9. **No server-side rate limits or quotas.** A research run may cost up to
   `MAX_PROVIDER_COST_USD_PER_RESEARCH_RUN` ($5), so this is a billing risk.
   Admin usage numbers are fixtures.
10. **Local-preview login lets anyone choose "admin".** Fine on localhost;
    make sure production builds cannot run in that mode.

### Code health

11. **Duplicate modules:** `domain/financial/calculations.py` vs
    `calculators.py`, `normalization.py` vs `normalizer.py`, and
    `domain/watchlist.py` beside the `domain/watchlist/` package (the package
    wins, so the file is dead code).
12. **About 5 MB of decorative PNGs** in `frontend/public/assets`
    (`evidence-texture.png` is 2.1 MB). Convert to WebP or CSS.
13. **Over-specification:** about 25 spec documents, 79 requirements and
    per-phase plans, but no end-to-end run on a real company.
14. **V1 scope is too wide:** comparisons, weekly Top 25, thesis tracker,
    tearsheets, Discover, News and admin, before one real report exists.

## Part 2: Making it a real product

Build one thin vertical slice first. Example: "enter a company, get a
verified one-page brief with every claim cited."

1. **Real Postgres.** Implement the existing repository Protocols with
   `psycopg` or SQLAlchemy against the Supabase migrations.
2. **Real data.** One official source first (SEC EDGAR/XBRL is free and
   half-built in `providers/financial/adapters.py`), plus one search
   provider and one extractor.
3. **Real LLM calls** for three jobs: extract claims, verify them against
   evidence, write the report. Use the existing Pydantic contracts as
   structured outputs; cache long source documents to keep cost down.
4. **A real worker.** Run the Postgres job queue in `jobs/queue.py` as a
   process and stream run progress to the UI.
5. **Replace the demo API client** on `/research` and `/reports/[id]`.
6. **Evaluations before features.** Hand-label about 50 claims across 10
   companies and measure verification accuracy.
7. Add more countries and features only after that works.

## Part 3: Business notes (original stock-research framing)

- Competition in AI financial research is heavy: AlphaSense, Hebbia, Rogo,
  Fintool, Brightwave, Perplexity Finance; Koyfin, Tikr and Quartr for data.
- The real differentiator is the README line: **"What companies say. What
  the evidence says."** Claim-level verification with an audit trail.
- Legal risks in the original framing:
  - A ranked Top 25 with scores may be treated as research recommendations
    under SEBI's Research Analyst Regulations (India) or as investment advice
    elsewhere. A footer disclaimer may not be enough.
  - Free-tier API terms (for example Finnhub) and most financial data
    licences restrict commercial redistribution and display.
  - "CONTRADICTED" labels on named companies carry defamation risk; keep the
    spec's careful wording.
  - Terms of Service, Privacy Policy and a DPA are needed before selling.

These concerns led to the pivot options in `02-PIVOT-OPTIONS.md`.
