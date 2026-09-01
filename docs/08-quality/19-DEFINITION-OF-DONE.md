# Definition of Done

A feature is not done because the UI appears to work. It is done when behavior, data, tests, security and documentation all agree.

## Universal Done Checklist

- Acceptance criteria from PRD/task are satisfied.
- Implementation follows relevant docs/ADRs.
- No new architectural coupling to provider-specific response shapes.
- Types/schema validations added at external boundaries.
- Unit/integration tests cover happy path and meaningful failure path.
- Error/empty/loading states implemented in UI if user-facing.
- Authorization checked for every new user-owned resource endpoint.
- Logs/metrics added for critical asynchronous/provider behavior.
- No secrets/API keys added to repo/client bundle/logs.
- Required lint/typecheck/tests/build commands pass.
- Docs/OpenAPI/schema updated if public behavior changed.
- No unresolved high-risk TODO in critical path.

## Research/Verification Feature Done

Additionally:
- self-reported vs independent evidence behavior is preserved
- missing evidence does not become contradiction
- source provenance saved
- provider failure is normalized
- prompt-injection fixture considered/tested if LLM reads source content
- deterministic logic used for arithmetic where possible
- score/verdict behavior has regression tests
- new factual report output maps to approved claims

## Provider Adapter Done

- official docs reviewed
- auth/key handling server-side
- timeout configured
- rate-limit behavior mapped
- retryable vs permanent errors mapped
- normalized result schema
- fixture contract tests
- provider request metadata/cost/latency recorded
- fallbacks defined
- terms/retention constraints noted

## Database Change Done

- migration committed
- FK/check/index reviewed
- RLS impact reviewed
- backward compatibility/deployment order considered
- schema doc updated
- destructive change has migration/backup plan

## UI Feature Done

- loading state
- empty state
- error state
- keyboard interaction
- status not dependent on color
- responsive behavior
- evidence/explanation reachable for any score/claim shown
- no misleading “trust/investment” wording

## Weekly Watchlist Done

- idempotent schedule/run
- staging vs published state
- eligibility quality gate
- failure cannot replace good current watchlist
- methodology version stored/displayable
- rank history preserved
- cost budget enforced
- fewer-than-25 case handled

## Release Gate

Before declaring an OJT milestone/release complete:
- citation verification coverage target passes
- conflict benchmark target passes at required milestone
- no known critical auth/SSRF/secret exposure issue
- golden research case runs end to end
- logs show run/provider lineage
- demo data clearly identifies uncertainty/limitations

