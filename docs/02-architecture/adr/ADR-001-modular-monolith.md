# ADR-001: Use a Modular Monolith First

**Status:** Accepted

## Context
The product contains many logical domains and third-party integrations, but is being built by a solo developer with AI coding agents. Microservices would add deployment, networking, schema ownership and observability complexity before scale is proven.

## Decision
Use one FastAPI codebase/process family organized into strong domain/provider modules. Workers may run as separate processes from the API but share the same codebase and database.

## Consequences
- Faster iteration and easier agent context.
- Transactions across truth-ledger entities remain simple.
- Module boundaries must be enforced in code review/tests.
- Split services later only after measured operational need.
