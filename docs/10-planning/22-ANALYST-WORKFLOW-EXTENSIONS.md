# Analyst Workflow Extensions

## Status and purpose

This extension adds the analyst work that surrounds an evidence-led report
without weakening the Truth Ledger. The initial implementation provides:

- research-intake modes: `INITIATION`, `UPDATE`, `EARNINGS`, `EVENT`,
  `SECTOR`, and `DILIGENCE`;
- an owner-scoped thesis tracker with a proposition, falsifier, materiality,
  and a separate research posture;
- cited earnings/filing change-brief projections; and
- a cited one-page tearsheet projection suitable for a print/PDF handoff.

The local UI uses explicit fixtures until a report has real source snapshots.
No fixture is presented as a live filing, price, estimate, or investment
conclusion. The database migration and API contract define the production
storage boundary; deployment against the configured PostgreSQL instance is a
release verification step.

## Product contract

### Research intake

A mode starts a workflow; it does not select a company, bypass conservative
entity resolution, or change a report's verification gate.

| Mode | Intended starting question |
|---|---|
| Initiation | What is the company, how does it make money, and what is the initial evidence posture? |
| Update | What has changed since the previous immutable report version? |
| Earnings | What changed in results, guidance, definitions, cash flow, and disclosed risks? |
| Event | What has a specific filing, rating action, management change, or other event affected? |
| Sector | Which comparable companies and disclosed sector conditions should be evaluated together? |
| Diligence | Which specific questions, adverse evidence, and source gaps remain before a decision? |

### Thesis tracker

Theses are analyst-authored propositions. Every thesis point has a falsifier.
Its status is `OPEN`, `SUPPORTED`, `WEAKENED`, or `UNCHANGED`; none of those
values are claim verdicts. Claim verdicts remain exactly `VERIFIED`,
`PARTIALLY_SUPPORTED`, `CONTRADICTED`, `UNVERIFIED`, `INSUFFICIENT_EVIDENCE`,
and `STALE`.

When a thesis becomes important to a report, the product must link it to exact
claim versions. It must not copy claim text into a mutable note or use an LLM
to turn a thesis status into a factual conclusion.

### Change brief and tearsheet

A production change brief line is only publishable when it names its evidence
snapshot(s), carries a retrieval timestamp, and clearly labels unsupported
items as open questions or limitations. The tearsheet is a concise projection
over report/claim/evidence records. It is never a canonical source of truth,
investment recommendation, trade signal, or automated execution interface.

## Later features

The following are intentionally documented as later work, not silently implied
by the current fixture-backed UX.

1. **Point-in-time financial market pack.** Licensed price, consensus, estimate,
   dividend, insider, and corporate-action data with exchange/calendar and
   timestamp lineage. Select vendors and coverage only after a licensing ADR.
2. **India listed-company pack.** NSE/BSE filings, MCA identity, SEBI disclosures,
   results calendars, and India-specific filing taxonomy. This needs source
   permissions, terms review, and a data-quality evaluation set first.
3. **Deterministic valuation workspace.** Reproducible ratio, bridge, scenario,
   and reverse-DCF calculations whose inputs are cited facts, periods, units,
   currencies, formula versions, and assumptions—not model-generated numbers.
4. **Event-triggered refresh.** Durable jobs that monitor permitted filing,
   result, rating, and official-news signals, deduplicate triggers, and create
   immutable report versions through the existing budget/freshness gates.
5. **Export pack.** PDF, DOCX, XLSX, and presentation exports that retain
   citations, limitations, report version, scoring version, and data-license
   attribution. Exports must not expose retained source content beyond policy.
6. **Team research workflow.** Review queues, assignees, comments, approval
   records, firm templates, and access-controlled shared workspaces. Add RLS,
   audit, retention, and privacy design before implementation.
7. **Portfolio and alert layer.** User-declared holdings/watchlists, materiality
   thresholds, and notification routing. It must remain research intelligence,
   not personalized advice or automated trading.

## Required release work before live use

- Apply and validate `docs/03-data/migrations/20260903_analyst_workflows.sql`
  against the target Supabase/PostgreSQL environment.
- Replace fixture projections only when a report is linked to persisted source
  snapshots and claim versions; preserve all retrieval and limitation metadata.
- Add integration tests against actual RLS policies and durable repository
  implementation, plus accessibility and print/PDF checks for the dedicated
  pages.
- Resolve data-provider and export licensing decisions in an ADR before enabling
  any paid, restricted, or market-data-backed workflow.
