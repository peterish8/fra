# Observability & Operations

## 1. Goals

We must be able to answer:
- Why did this report fail or become partial?
- Which provider was slow/broken?
- Why does this claim have this verdict/score?
- How much did a research run cost?
- Did a weekly cron publish incomplete data?
- Can the run be safely retried?

## 2. Structured Logs

Use JSON logs to stdout. Common fields:
- `timestamp`
- `level`
- `service`
- `request_id`
- `user_id` hashed/redacted where appropriate
- `report_id`
- `research_run_id`
- `job_id`
- `stage`
- `provider`
- `provider_request_id`
- `duration_ms`
- `status`
- `error_code`

Never log API keys, bearer tokens, raw cookies or sensitive headers.

## 3. Tracing

Trace a research run through:
```text
HTTP create/refresh
 -> job enqueue
 -> entity resolution
 -> registry calls
 -> search calls
 -> extraction
 -> LLM calls
 -> verification
 -> scoring
 -> synthesis
 -> report publication
```

Use OpenTelemetry-compatible trace IDs where possible.

## 4. Metrics

### API
- request rate
- p50/p95 latency
- 4xx/5xx
- auth failures

### Worker/jobs
- queue depth
- job age
- success/partial/failure rate
- attempts/retries
- stage duration
- active leases

### Providers
- success/no-result/rate-limit/error rates
- latency
- estimated cost
- evidence yield per call
- parse failure rate

### Research quality
- citation verification coverage
- verified/partial/contradicted/unverified counts
- evidence coverage
- source-family diversity
- conflicts per report
- publication-gate failure reasons

### Weekly watchlist
- candidates discovered
- candidates eligible
- deep-research finalists
- published count
- ranking churn
- total run cost/duration

## 5. Alerts

Alert on:
- provider error/rate-limit spike
- weekly watchlist failed to publish by deadline
- queue age above threshold
- publication gate unexpectedly dropping
- research failure rate spike
- cost/day above budget
- database connection saturation
- Sentry high-severity backend/frontend exceptions

## 6. Provider Health Dashboard

Internal view:
```text
Provider | Operation | 1h success | p95 | 429% | cost/call | circuit state
```

Provider health can influence routing order but cannot change evidence semantics.

## 7. Cost Accounting

Store estimated provider cost per request/run/watchlist. Dashboard by:
- provider
- operation
- user
- research depth
- weekly pipeline

Hard budgets enforced in orchestration; dashboards are not the only control.

## 8. Run Debugging

A run detail page/internal endpoint should show:
- stage timeline
- provider calls/statuses
- source counts
- follow-up loops
- blockers
- cost
- output records created

This is for operations; do not expose raw internal prompts/secrets to ordinary users.

## 9. Backups & Recovery

- Supabase/Postgres production backups enabled per plan.
- Before destructive schema migrations, verify restore path.
- Report/source versions are immutable enough to support audit/recovery.
- Weekly watchlist can revert pointer to last known-good published run.

