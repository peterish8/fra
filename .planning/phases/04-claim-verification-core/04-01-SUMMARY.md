# Plan 04-01 Summary — Validated Facts, Claims, and Evidence

Completed: 2026-09-01

## Delivered

- Versioned Pydantic envelopes for company claims and financial facts, with malformed-output rejection and untrusted-evidence delimiters.
- Typed facts that preserve raw representation, null/unknown values, accounting context, periods, entity scope, extraction confidence, and schema/prompt lineage.
- Atomic claim construction with stable identity, append-only superseding versions, and explicit evidence role/directness/independence links to source snapshots.
- Forward-only database provenance additions for fact-to-claim links, claim kinds, extraction metadata, confidence constraints, and immutable truth records.

## Verification recorded by workers

- Claim/fact contracts: 14 passed.
- Backend suite reported before final integration: 224 passed; Ruff and mypy passed.

## Deferred integration

- A PostgreSQL repository must enforce source-snapshot existence and self-reported independence rules when it persists these in-memory domain contracts.
- Claim inspection HTTP endpoints and semantic verification/publication gates are the next plan.
