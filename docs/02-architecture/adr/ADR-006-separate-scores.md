# ADR-006: Use Separate Explainable Scores

**Status:** Accepted

## Context
A single “trust score” would mix research quality, company disclosure behavior and business/financial performance and could mislead users.

## Decision
Expose separate Claim Confidence, Research Confidence, Evidence Coverage, Disclosure Reliability and Financial/Business/Watchlist scores. Each score is versioned and explainable.

## Consequences
- More nuanced UI.
- Prevents “missing data = bad company” mistakes.
- Score logic requires explicit configuration and tests.
