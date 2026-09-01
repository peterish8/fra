# High-Level Design (HLD)

## 1. System Context

```mermaid
flowchart LR
    U[Researcher] --> WEB[Next.js Web App]
    WEB --> API[FastAPI Backend]
    API --> DB[(Supabase PostgreSQL)]
    API --> Q[Durable Job Queue]
    W[Python Research Worker] --> Q
    W --> DB
    W --> P[Search / Research Providers]
    W --> G[Government / Registry Sources]
    W --> F[Financial Data Providers]
    W --> X[Extraction / Browser Providers]
    W --> L[LLM Provider]
    S[Weekly Scheduler] --> Q
```

## 2. Container Responsibilities

### Next.js Web App
- Authentication UI/session integration.
- Report library/sidebar.
- Research creation form and comparison flow.
- Live/polled research progress.
- Report reader, score cards, claims-vs-evidence table, evidence drawer, conflicts, history/diff.
- Weekly Top 25 discovery dashboard.
- No provider API keys and no direct external research calls.

### FastAPI Backend
- Auth/authorization boundary.
- User/report/company CRUD.
- Research-run creation and idempotency.
- Read APIs for stored results.
- Enqueues long-running work.
- Validates publication gates.

### Research Worker
- Research orchestration/state machine.
- Company/entity resolution.
- Provider routing/fallbacks.
- Extraction/fact/claim generation.
- Verification, conflicts, adversarial research, scoring.
- Report synthesis/versioning.
- Weekly watchlist funnel.

### PostgreSQL
- Canonical companies, source snapshots, claims/evidence/facts.
- Research/report versions.
- Scores and algorithm version.
- Jobs/audit events/provider calls.

## 3. End-to-End User Research Flow

```mermaid
flowchart TD
    A[User creates research workspace] --> B[Create Report + ResearchRun]
    B --> C[Entity Resolver]
    C --> D{Confident legal entity?}
    D -- No --> E[Return candidates / insufficient identity]
    D -- Yes --> F[Registry Verification]
    F --> G[Discover official company domains]
    G --> H[Extract public company-owned claims]
    H --> I[Independent research plan]
    I --> J[Perplexity Search + other search fallbacks]
    J --> K[Official filings + Financial APIs]
    K --> L[Optional Gemini Deep Research for deep/high-materiality work]
    L --> M[Source normalization + source-family dedupe]
    M --> N[Fact extraction]
    N --> O[Atomic claim versions]
    O --> P[Semantic + numeric + temporal verification]
    P --> Q[Conflict detection/classification]
    Q --> R[Adversarial challenge for eligible claims]
    R --> S{Evidence sufficient?}
    S -- No --> T[Follow-up research loop]
    T --> M
    S -- Yes/limit reached --> U[Deterministic scoring]
    U --> V[Report synthesis from approved claims]
    V --> W[Publication gate]
    W --> X[Immutable ReportVersion]
```

## 4. Self-Reported vs Independent Evidence

```mermaid
flowchart LR
    CW[Company Website / Company PR] --> SR[SELF_REPORTED Claim]
    SR --> V[Verifier]
    GOV[Government / Regulator] --> V
    FIL[Official Filing / Audited Statement] --> V
    FIN[Financial API] --> V
    IND[Independent Web / Research] --> V
    V --> O[Claim Verdict + Confidence]
```

Rule: `CW` can prove that the company **said** something, but cannot independently prove the underlying statement.

## 5. Provider Routing Architecture

```text
Research Need
   |
   +-- Web discovery -------- Perplexity -> Brave -> Exa -> Tavily(optional)
   +-- Page extraction ------ Firecrawl -> Exa Contents -> Browserless/Zyte
   +-- Deep research -------- Gemini Deep Research -> custom multi-search loop
   +-- US registry/filings -- SEC EDGAR
   +-- UK registry ---------- Companies House -> GLEIF/OpenCorporates
   +-- India registry ------- MCA/data.gov.in adapters -> GLEIF/OpenCorporates
   +-- Global identity ------ country registry -> GLEIF -> OpenCorporates
   +-- Financial facts ------ official filing/XBRL -> EODHD -> Twelve Data
   +-- News discovery ------- Perplexity/Brave -> GDELT
```

Provider output is normalized before domain logic. The domain never relies on provider-specific response shapes.

## 6. Truth Ledger

The Truth Ledger is the core product model:

```text
Company
  -> Fact(s)
  -> Claim
      -> ClaimVersion(s)
          -> Evidence relations
          -> Semantic verification
          -> Numeric verification
          -> Temporal verification
          -> Conflicts
          -> Adversarial result
          -> Confidence score
          -> Freshness state
```

Reports reference claim versions rather than duplicating truth.

## 7. Report Versioning

```mermaid
flowchart LR
    R[Report Workspace] --> V1[Version 1]
    R --> V2[Version 2]
    R --> V3[Version 3 Current]
    V1 --> D[Diff Engine]
    V2 --> D
    V3 --> D
```

A refresh creates a new `ResearchRun` and, if successful, a new immutable `ReportVersion`. Old versions and score versions remain accessible.

## 8. Weekly Watchlist Architecture

```mermaid
flowchart TD
    A[Weekly Scheduler] --> B[Discover hundreds of candidates]
    B --> C[Entity dedupe + validity]
    C --> D[Cheap metadata/financial/news screen]
    D --> E[Shortlist]
    E --> F[Medium verification]
    F --> G[Deep finalists]
    G --> H[Full research + adversarial verification]
    H --> I[Stage-aware scoring]
    I --> J{Quality threshold met?}
    J -- Yes --> K[Publish ranked entries atomically]
    J -- No --> L[Exclude; list may contain <25]
```

No candidate is ranked solely because of news volume or company PR. Source independence, evidence coverage and business-stage normalization are part of eligibility/scoring.

## 9. C4 Component View: Research Worker

```mermaid
flowchart LR
    O[Orchestrator] --> ER[Entity Resolver]
    O --> RP[Research Planner]
    RP --> PR[Provider Router]
    PR --> SP[Source Processor]
    SP --> FE[Fact Extractor]
    FE --> CB[Claim Builder]
    CB --> VM[Verification Manager]
    VM --> SV[Semantic Verifier]
    VM --> NV[Numeric Validator]
    VM --> TV[Temporal Validator]
    VM --> CD[Conflict Detector]
    VM --> AV[Adversarial Verifier]
    VM --> FR[Follow-up Research]
    VM --> SC[Scoring Engine]
    SC --> RS[Report Synthesizer]
```

## 10. Deployment View

```text
Browser
  -> Vercel (Next.js)
       -> Persistent FastAPI service
            -> Supabase Postgres/Auth
            -> enqueue jobs
       Python Worker(s)
            -> provider APIs / permitted public internet
            -> Supabase Postgres

Scheduler (hosting cron / Supabase pg_cron / equivalent)
  -> enqueue weekly watchlist job
```

## 11. Scaling Strategy

V1: one API service + one or a few worker processes + PostgreSQL queue.

Scale when measured:
- increase worker concurrency per provider budget/rate limits;
- partition jobs by type/priority;
- add Redis/managed queue only when Postgres queue becomes bottleneck;
- separate crawler workers from LLM/deep-research workers only if load isolation is needed;
- use object storage for large source snapshots if database size warrants it.

## 12. Failure Philosophy

A provider failure is data about the run, not permission to guess.

Fallback chain ends in explicit status:
`NO_RESULTS`, `ACCESS_RESTRICTED`, `SOURCE_UNAVAILABLE`, `INSUFFICIENT_EVIDENCE`, or `PARTIAL`.

The system should be useful even when it concludes it cannot make a high-confidence statement.

