# ADR-005: Durable Asynchronous Research Jobs

**Status:** Accepted

## Context
Deep research and multi-provider verification can take minutes and cannot safely live inside a single browser/serverless request.

## Decision
Research/refresh/watchlist operations enqueue durable jobs. Workers checkpoint stage progress in PostgreSQL and use idempotency/leases/retries.

## Consequences
- Reliable recovery from process/provider failures.
- UI needs progress polling/SSE.
- Job design is more work than synchronous endpoints but avoids timeout/data-loss risk.
