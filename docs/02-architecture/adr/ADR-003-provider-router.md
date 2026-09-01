# ADR-003: Provider Adapters Behind a Router

**Status:** Accepted

## Context
Search, extraction, deep research, financial data and registries can fail, change pricing, rate limit or have different coverage.

## Decision
All external integrations implement normalized adapter contracts. Domain code asks for capabilities (search, extract, registry lookup, financial metric), while a router chooses primary/fallback providers under health, policy and cost constraints.

## Consequences
- Easier fallback/provider replacement.
- Provider agreement cannot be confused with source agreement.
- Contract fixtures are required for each adapter.
