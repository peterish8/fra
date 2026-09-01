# Standards & AI-Agent Development Workflow

## Why this documentation pack is structured this way

The project is intended to be built by a solo developer using coding agents, so durable repository context matters more than one enormous prompt.

### Spec-driven development
GitHub Spec Kit describes a default sequence of **Spec → Plan → Tasks → Implement**, with Markdown artifacts feeding later phases. This pack follows the same idea: PRD/TRD/HLD define intent and constraints, backlog defines bounded work, and implementation agents are required to verify against Definition of Done.

Reference: https://github.github.com/spec-kit/

### Repository agent instructions
OpenAI documents `AGENTS.md` as repository guidance that can tell Codex how to navigate a codebase, test it and follow project practices. GitHub Copilot and Cursor also support repository/project instructions. Therefore `AGENTS.md` is intentionally short enough to act as a routing contract into detailed `docs/` rather than duplicating the entire specification.

References:
- https://openai.com/index/introducing-codex/
- https://docs.github.com/en/copilot/how-tos/configure-custom-instructions-in-your-ide
- https://docs.cursor.com/context/rules-for-ai

### Architecture communication
C4 recommends hierarchical views (system context, containers, components, code) and notes that context/container diagrams are sufficient for many teams. The HLD uses context/container/component-style diagrams rather than documenting every class.

Reference: https://c4model.com/

### Architecture decisions
ADRs preserve why an architecturally significant decision was made and its trade-offs. This pack records choices such as modular monolith, no MCP, and no vector DB in V1.

Reference: https://adr.github.io/

### Security
OWASP ASVS is used as a practical basis for web application security requirements; OWASP API Security Top 10 informs API-specific threats such as broken object authorization, resource consumption, SSRF and unsafe third-party API consumption.

References:
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/API-Security/

### AI risk/evaluation
NIST AI RMF and its Generative AI profile emphasize lifecycle risk management, evaluation/verification/validation and trustworthy AI characteristics. For this project, the practical interpretation is: measure citation/conflict/numeric behavior, preserve provenance, test adversarial/prompt-injection cases, expose uncertainty, and version model/prompt changes.

References:
- https://www.nist.gov/itl/ai-risk-management-framework
- https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence

## Recommended solo-dev agent loop

For every bounded feature:

```text
Requirement/task
  -> agent reads relevant specs
  -> implementation plan
  -> tests/contract first where deterministic
  -> implementation
  -> validation commands
  -> diff/spec drift review
  -> docs/schema/API updates
  -> merge
```

Do not keep all product knowledge in `AGENTS.md`; that wastes context and increases drift. `AGENTS.md` tells agents **where to look and what rules are non-negotiable**, while detailed durable knowledge stays in focused documents.
