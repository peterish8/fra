# Data Governance, Provenance & Legal/Policy Boundaries

## 1. Purpose

The product's credibility depends on knowing **where information came from, when it was retrieved, what we are permitted to retain, and what the system is actually claiming**.

This document is not jurisdiction-specific legal advice; it defines product engineering guardrails.

## 2. Provenance Requirements

Every material fact/claim must be traceable to:
- source/document identity
- source snapshot/retrieval timestamp
- evidence excerpt/location where permitted
- extraction method/provider
- research run
- verification records
- score/config versions

For derived metrics also store formula/version and input facts.

## 3. Source Retention

Preferred retention order:
1. source metadata + canonical URL/document identifier
2. content hash
3. evidence excerpt necessary for audit
4. permitted extracted text or object-storage snapshot

Do not assume permission to permanently store an entire crawled page/article merely because it was public. Provider/source terms may require restricted retention.

## 4. Company-Owned Content

Company-owned public content is stored/classified as `SELF_REPORTED` for underlying company claims.

It is useful for:
- understanding company positioning
- extracting explicit claims
- comparing disclosure over time

It is not independent confirmation of itself.

## 5. Restricted Access

The product must not intentionally bypass:
- authentication
- paywalls
- CAPTCHA
- private APIs
- access-control mechanisms
- prohibited automated-access restrictions

Use official APIs, public open data, licensed providers, permitted public extraction, or report `ACCESS_RESTRICTED`.

## 6. Government/Registry Data

Government data receives strong authority for facts within its remit but still records:
- dataset/registry name
- freshness/retrieval date
- jurisdiction
- registration ID
- source URL/document

A stale government dataset is not silently treated as current.

## 7. User Data

User-specific:
- account/profile
- private report workspace metadata
- favorites/search history if implemented
- private generated reports

Apply minimum necessary retention and authenticated access. Do not use private user report data to train external models unless product policy explicitly allows and users are informed.

## 8. Public vs Private Reports

Default: user reports private.

If share/public feature is added:
- explicit user action
- revocable sharing
- no provider secret/internal debug data
- source excerpts limited to permitted presentation
- public URL uses opaque share ID and authorization model

## 9. Non-Advice Positioning

Weekly ranking and company scores are research/discovery tools, not personalized financial advice.

Preferred wording:
- Research Watchlist
- Evidence-backed momentum
- Financial/Business Score
- Research Confidence

Avoid:
- “Buy”/“Sell” recommendations
- guaranteed return language
- personalized investment suitability
- “safest investment”

## 10. Claims About Misconduct

System-level wording should distinguish:
- `UNVERIFIED`
- `CONTRADICTED BY CURRENT EVIDENCE`
- `OFFICIAL INVESTIGATION REPORTED`
- `REGULATOR FINDING`
- `COURT JUDGMENT`

Do not convert a data mismatch into “fraud” or “lying.” Material contradictions are facts about evidence disagreement, not moral/legal conclusions.

## 11. Corrections

If source/verification error is discovered:
- preserve original report version for audit
- create corrected claim/source/verification version
- generate superseding report version
- show change reason
- do not rewrite historical evidence invisibly

## 12. Data Export/Deletion

If required by product/account policy:
- export user-owned report metadata/content
- delete/de-identify user-owned workspace data
- shared public-source evidence may remain if independently collected and legally/policy permitted

## 13. Provider Licensing Checklist

Before enabling a provider in production:
- confirm commercial use terms
- confirm display/attribution requirements
- confirm caching/retention rights
- confirm rate limits
- confirm whether end-user redistribution is permitted
- document cost/plan dependency

## 14. Privacy/Security Documentation

Before public launch, add:
- Privacy Policy
- Terms of Use
- Research methodology page
- Data/source attribution methodology
- disclaimer that confidence/ranking reflects available evidence and methodology version

