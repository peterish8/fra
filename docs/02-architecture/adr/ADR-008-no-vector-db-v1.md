# ADR-008: Do Not Add a Vector Database in V1

**Status:** Accepted

## Context
The project can perform targeted web/filing extraction and store structured claims/evidence without maintaining a vector database initially. Adding one increases operational/data-consistency complexity.

## Decision
Use PostgreSQL + full-text/trigram indexes and targeted document extraction first. Introduce vector retrieval only if measured long-document retrieval quality/latency requires it.

## Consequences
- Simpler V1 stack.
- Long filings may use section/chunk retrieval through provider/document logic.
- Any future vector store requires a new ADR and source-version synchronization design.
