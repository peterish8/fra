# Plan 06-01 Summary — Durable Jobs and Research Run Lifecycle

Completed: 2026-09-02

## Delivered

- Typed durable job records with atomic in-memory semantics and a PostgreSQL DB-API adapter using `FOR UPDATE SKIP LOCKED`.
- Lease claim, heartbeat, expiry, completion, retry/permanent failure, cancellation, priority, bounded backoff/jitter, idempotency, and sanitized error contracts.
- Resumable research-run and stage state machine with checkpoint-before-transition ordering, terminal partial/failure/cancelled outcomes, budget limits, and duplicate report-version protection.
- Forward migration and schema documentation linking jobs to research runs and restricting queue state to the service role.
- Queue and lifecycle fixture tests covering crash recovery, replay, retry, budget exhaustion, cancellation, and report-version deduplication.

## Verification

- Queue/lifecycle production files were individually linted and compiled by the implementation lanes.
- Queue/lifecycle focused tests: 13 passed, with one existing Starlette/httpx deprecation warning.

## Deferred integration

- A production repository must bind the lifecycle protocol to PostgreSQL transactions and expose an owner-authorized run-status endpoint.
- Worker deployment, provider health, and credentialed failure recovery remain for later operational and credentialed validation.
