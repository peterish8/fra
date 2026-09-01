# ADR-007: No MCP/Product Plugin Layer

**Status:** Accepted

## Context
Earlier concepts included MCP/ChatGPT integration, but current product scope is a full website where server-side APIs/providers perform research and verification.

## Decision
Do not implement MCP in V1/OJT scope. All third-party integrations are backend API/provider adapters used by the website and scheduled jobs.

## Consequences
- Smaller scope and clearer security model.
- A future external API/plugin can reuse backend services if later required.
