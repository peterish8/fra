# Phase 10 Release Evaluation

This is the reproducible hardening and evaluation record for the OJT release.
Fixtures are synthetic or minimal permitted excerpts; no paid provider or
credential is required for the local gate.

## Blocking local gates

| Gate | Threshold | Executable coverage |
|---|---:|---|
| Citation verification coverage | 100% | `backend/tests/evaluation/test_phase10_evaluation.py` |
| Conflict classification | >=90% | `backend/tests/conflicts/fixtures/conflict_cases.json` |
| Deterministic numeric validation | >=99% | `backend/tests/fixtures/financial_cases.json` |
| Auth/object authorization | 100% denial for cross-user/anonymous cases | `backend/tests/security/`, existing RLS contracts |
| SSRF/redirect/DNS rebinding | all corpus cases blocked or allowed as labeled | `backend/tests/security/test_url_policy_contract.py` |
| Prompt injection/schema safety | no tool or secret behavior from evidence | `backend/tests/evaluation/`, `backend/tests/security/` |
| Chaos/idempotency | no duplicate job/version or lost lease mutation | `backend/tests/chaos/` |
| Browser critical paths | route, report, evidence, filter, empty/partial contracts | `frontend/tests/e2e/` |

Failures remain visible by case ID. An aggregate percentage never suppresses a
failed case.

## Current execution record (2026-09-02)

- Phase 10 backend target (`uv run ... pytest -q tests/evaluation
  tests/security/test_phase10_hardening.py tests/chaos`): **29 passed**. This
  includes 3 citation gate cases (the two negative cases correctly blocked),
  11 conflict labels at/above the 90% gate, 16 numeric cases at/above the 99%
  gate, entity-abstention cases, 11 hardening/quota checks, and 7 provider/
  worker/cron/budget chaos checks.
- Full backend suite through the same ephemeral `uv` environment: **356
  passed, 12 failed**. The failures are existing queue-clock and semantic
  verifier contract mismatches in `tests/jobs/test_queue_contracts.py` and
  `tests/verification/test_semantic_verification.py`; this remains a release
  blocker until the owning implementation/tests converge.
- Frontend Vitest (`node_modules/.bin/vitest.cmd run`): **16 passed** across
  four files, including the new 5-test critical-flow contract. The normal
  `npm` shim is **UNAVAILABLE** because it points to a missing `npm-cli.js`.
- Live Supabase/PostgreSQL RLS, provider 429/timeout/outage tests, browser
  automation, accessibility scanner, and responsive visual review: **NOT RUN**
  because no live services/runner are configured. Fixture and static contracts
  must not be reported as live verification.

## Release decision

The Phase 10 code/test artifacts are complete, but release approval remains
**BLOCKED** until the unavailable commands and live checks above execute in CI
or a configured staging environment. This preserves the project's rule that a
build or fixture result cannot imply runtime, provider, RLS, accessibility, or
responsive readiness.
