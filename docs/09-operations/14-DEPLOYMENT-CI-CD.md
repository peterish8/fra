# Deployment & CI/CD

## 1. Environments

- `local`
- `preview/staging`
- `production`

Separate database/project and provider credentials between staging and production where practical.

## 2. Hosting

### Frontend
Vercel.

### Backend/Worker
Persistent Python host capable of:
- FastAPI ASGI service
- long-running worker process
- outbound provider network access
- configurable concurrency

Do not rely on a short-lived serverless request for Gemini Deep Research or multi-stage research runs.

### Database/Auth
Supabase Postgres/Auth.

## 3. Git Workflow

For solo development with coding agents:
- `main` is releasable.
- features/fixes use branches/worktrees where agent tooling supports it.
- each change has a clear task/issue and spec reference.
- no direct unreviewed agent commits to production branch for high-risk schema/security/scoring work.

## 4. CI Pipeline

On PR/push:
1. install pinned dependencies
2. frontend lint
3. frontend typecheck
4. frontend unit/component tests
5. frontend production build
6. backend format check
7. backend lint
8. backend typecheck
9. backend unit/integration tests
10. schema/migration checks
11. OpenAPI validation
12. secret scan
13. dependency/security scan
14. critical research-eval smoke tests

## 5. Deployment Order

For compatible migrations:
1. deploy additive DB migration
2. deploy backend supporting old/new as necessary
3. deploy frontend
4. enable new feature/config

For breaking changes use expand/contract; avoid DB migration that immediately breaks current production code.

## 6. Database Migrations

- migration files checked into git
- never edit already-applied production migration
- index large tables carefully
- backfill separately from schema change when expensive
- scoring methodology changes do not rewrite historical score rows

## 7. Secrets

- hosting platform secret stores/env vars
- `.env.example` contains names only
- git secret scanning
- separate keys per environment where provider supports it
- rotation procedure documented

## 8. Scheduled Jobs

Weekly watchlist scheduler should only enqueue an idempotent durable job.

Example:
```text
cron trigger
 -> enqueue WATCHLIST_WEEKLY:{week_id}
 -> worker performs staged funnel
 -> validate
 -> atomic publish
```

A duplicate cron event must map to same idempotency key.

## 9. Feature Flags / Config Activation

Use config or feature flags for:
- new provider adapter
- new score methodology
- new country adapter
- expensive deep-research behavior

Roll out independently from code deploy where useful.

## 10. Release Checklist

- CI green
- migrations applied/verified
- provider credentials configured
- health endpoint green
- one staging research golden case passes
- publication gate works
- error tracking receives events
- rollback/revert plan known

