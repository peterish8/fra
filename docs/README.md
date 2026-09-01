# Documentation Index

This folder contains the detailed specifications used by coding agents and human reviewers.

## Recommended reading order

### Product and scope
1. `00-project/00-STANDARDS-AND-AI-WORKFLOW.md`
2. `00-project/01-PRD.md`
3. `01-technical/02-TRD.md`

### Architecture and contracts
4. `02-architecture/03-ARCHITECTURE-HLD.md`
5. `02-architecture/adr/README.md` and relevant ADRs
6. `03-data/04-DATABASE-SCHEMA.md`
7. `03-data/schema.sql`
8. `04-api/05-API-SPEC.md`
9. `04-api/openapi.yaml`

### Research engine
10. `05-research-engine/06-RESEARCH-VERIFICATION-SPEC.md`
11. `05-research-engine/07-SCORING-RANKING-SPEC.md`
12. `05-research-engine/08-PROVIDER-ROUTING-FALLBACKS.md`
13. `05-research-engine/20-LLM-CONTRACTS.md`

### Product design
14. `06-product-design/09-UI-UX-SPEC.md`
15. `06-product-design/10-DESIGN-SYSTEM.md`

### Safety, quality and operations
16. `07-security-governance/11-SECURITY-THREAT-MODEL.md`
17. `07-security-governance/16-DATA-GOVERNANCE-LEGAL.md`
18. `08-quality/12-TESTING-EVALUATION.md`
19. `08-quality/15-EDGE-CASES.md`
20. `08-quality/19-DEFINITION-OF-DONE.md`
21. `09-operations/13-OBSERVABILITY-OPERATIONS.md`
22. `09-operations/14-DEPLOYMENT-CI-CD.md`

### Implementation planning
23. `10-planning/17-IMPLEMENTATION-PLAN.md`
24. `10-planning/18-TASK-BACKLOG.md`
25. `10-planning/21-OPEN-DECISIONS.md`

## Agent rule

Agents should load only the documents relevant to the current task after reading `../AGENTS.md`. Product or architecture behavior must not be silently changed in code; update the corresponding spec/ADR first.
