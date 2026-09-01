# ADR-002: PostgreSQL Truth Ledger Is Canonical State

**Status:** Accepted

## Context
A generated report alone cannot support auditability, refreshes, version diffs, conflict resolution or claim-level confidence.

## Decision
Store companies, source snapshots, facts, claims, evidence, verification records, scores and report versions in PostgreSQL. Report prose is a projection over these records.

## Consequences
- Living reports and diffs are possible.
- Schema is richer than a simple chat/report app.
- Historical records should be append/version oriented.
