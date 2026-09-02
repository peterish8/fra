# Release readiness and operator runbook

Operators diagnose runs using run ID, stage, provider, status, duration, cost, and degradation reason. Diagnostics are redacted for prompts, cookies, bearer tokens, API keys, and secrets. A failed or partial run is retried from the durable checkpoint; a failed watchlist staging job cannot replace the published pointer.

## Gate checklist

- CI lint, typecheck, fixture tests, migrations, security checks
- Backup and additive migration verification
- Provider credentials/licensing and rate-limit configuration
- API/worker health checks and safe diagnostics smoke test
- Complete and insufficient-evidence golden research cases
- Publication gate, watchlist revert, and rollback rehearsal

Live Supabase/provider checks remain setup blockers until credentials and infrastructure are supplied.
