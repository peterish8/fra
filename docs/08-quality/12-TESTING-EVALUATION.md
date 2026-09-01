# Testing & Evaluation Plan

## 1. Testing Pyramid

### Unit tests
Target deterministic logic heavily:
- currency/unit normalization
- lakh/crore conversions
- period normalization
- numeric tolerance
- growth/margin/ratio formulas
- conflict classification rules
- scoring formulas
- freshness rules
- source-family dedupe helpers
- publication gates

### Provider contract tests
Each adapter uses recorded/synthetic fixtures to test:
- successful normalization
- no-results
- rate-limit
- malformed payload
- provider schema drift
- timeout/retry classification

Do not make CI depend on live paid APIs by default.

### Integration tests
- report creation → research job enqueue
- research stage persistence
- source → fact → claim → evidence → verification pipeline
- report version publication gate
- user authorization/RLS
- refresh creates new version without overwriting old version
- weekly watchlist staging/publication

### End-to-end tests
Critical browser paths:
1. sign in
2. create research workspace
3. entity ambiguity flow
4. research progress
5. open completed report
6. inspect evidence drawer
7. filter contradicted claims
8. refresh report
9. compare versions
10. browse weekly watchlist

## 2. OJT Evaluation Targets

### Citation verification coverage
Metric:
```text
claims_with_required_citation_verification / factual_cited_claims_in_verified_report
```
Target: **100%**.

Coverage is not correctness. Also manually/automatically evaluate whether the verifier verdict is correct.

### Conflict detection
Curated labeled cases with:
- genuine value conflict
- only period mismatch
- only currency/unit mismatch
- GAAP/non-GAAP
- parent/subsidiary scope mismatch
- restatement
- compatible rounded values

Target: **>=90% correct conflict flagging/classification** on the project evaluation set.

## 3. Additional Evaluation Suites

### Numeric validator
Minimum cases:
- 130,497M vs 130.497B
- crore/lakh conversions
- parentheses negatives
- percentages/basis points
- zero vs missing
- rounded numbers
- wrong currency
- fiscal year mismatch
- YoY calculation
- divide-by-zero/invalid ratios

Target: >=99% on deterministic fixture set.

### Entity resolution
Cases:
- same company, common name/ticker
- same name in different countries
- former name
- parent/subsidiary
- acquisition/merger
- no legal entity found
- fake/copycat domain

Measure precision/abstention. Incorrect confident merge is worse than asking for clarification.

### Source independence
Cases:
- Reuters syndicated to many sites
- company press release copied by news/blogs
- two search providers returning same underlying article
- genuinely independent filing + news + financial API

### Claim verification
Create human-labeled claim/evidence pairs:
- direct support
- partial support
- unsupported
- contradiction
- insufficient context
- estimate vs fact
- future guidance vs realized metric

### Prompt-injection resistance
Web fixtures include malicious instructions requesting:
- secret disclosure
- tool invocation
- ignoring evidence rules
- changing verdict

Expected: treated only as page content; no policy/tool behavior change.

## 4. Golden Research Cases

Maintain a small reproducible benchmark set, e.g.:
- large US public company with rich SEC data
- Indian listed/private entity with MCA/official-data needs
- UK company using Companies House
- startup with sparse financial disclosure
- company with no verified website
- company with name ambiguity
- company with a known restatement/conflicting metrics

Do not rely only on famous/easy public companies.

## 5. LLM Evaluation

For extraction/verifier prompts track:
- schema-valid rate
- precision/recall against labeled facts/claims
- unsupported claim rate
- evidence span quality
- model/prompt version
- cost and latency

Any prompt/model change affecting critical outputs must run regression eval before production activation.

## 6. UI Quality Tests

- accessibility automated scan + keyboard manual pass
- visual regression for key report screens
- responsive widths
- long company names/claims
- 0/1/1000+ claims
- very large financial numbers
- `NOT_ENOUGH_DATA` score state
- dark/status color contrast if dark mode added

## 7. Load/Chaos Tests

Before final OJT demo/release:
- concurrent research runs
- provider 429s
- provider timeout
- one provider completely unavailable
- worker crash mid-stage
- lease expiry/retry
- duplicate cron trigger
- budget exhaustion
- database temporary error

Success criterion: no silent data corruption/duplicate published versions.

## 8. Test Data Policy

- Prefer synthetic/fixture source content in unit/integration tests.
- Do not commit API keys.
- Do not commit copyrighted full-source dumps unless permitted.
- Golden test references should use minimal necessary excerpts/metadata.

## 9. CI Gates

Pull request must pass:
- frontend lint/typecheck/tests/build
- backend format/lint/typecheck/tests
- migration/schema validation
- OpenAPI parse validation
- security/secret scan
- targeted evaluation smoke tests

Release/main deployment additionally runs broader integration/evaluation suites as cost/time permits.

