# Pivot options without investment advice (2026-10-07)

> Superseded in part by `03-PAIN-POINT-VALIDATION.md`, which checks these
> ideas against competitors and corrects the pricing and positioning below.

## The core idea

SEBI rules (and similar rules elsewhere) mainly apply when a product tells
people **what to do with listed securities**: buy/sell/hold calls, price
targets, ranked stock lists, paid tips. Keep the financial research agent,
but point it at a business question: **"Is this company safe to do business
with?"** Customers become businesses making business decisions, not
investors making trades.

The strongest existing code (entity resolution, registry adapters, the
claim-vs-evidence engine, conflict detection, living reports) fits this
better than it fits stock research.

## Five directions

| # | Idea | Who pays | Why it is not investment advice |
|---|---|---|---|
| 1 | **Counterparty check agent** — check a company before signing, lending or shipping on credit | SMEs, exporters, B2B sales, procurement, NBFC/fintech lenders | Researches a business partner; no securities |
| 2 | **Disclosure pre-check** — a company uploads a draft press release or investor deck; every number is checked against its own filings | Listed companies' IR, CFO and company secretary teams | The customer is the issuer; it is proofreading |
| 3 | **CA / accountant reconciliation agent** — books vs GST returns vs bank statements | CA firms, bookkeepers | Uses the client's own data; no data licensing issue |
| 4 | **Competitor intelligence** — what competitors claim vs what is true | Founders, sales and strategy teams | Market research |
| 5 | **Learn-finance tutor** — learn to read real annual reports, no opinions | Students, colleges | Education only; lowest revenue |

## Original pick: counterparty check (#1)

- **Input:** company name, CIN, GSTIN or website.
- **Output:** a one-page evidence report:
  - identity (entity exists, is active, matches GSTIN and website);
  - claims vs verification (age, size, turnover), each verified, partial,
    contradicted or unverified, with a source;
  - red flags as evidence, not judgment (all directors recently changed,
    shared address with many companies, lender charges, court cases, late
    filings, cancelled GST registration);
  - monitoring alerts when any of these change.
- **Keep:** `companies/resolver.py`, registry adapters, source ledger,
  claims/verification, conflicts, `sources/freshness.py`, lakh/crore
  normalization.
- **Delete:** Top 25 watchlist, Discover, thesis tracker, tearsheet.
- **Add:** Indian data via **licensed** API providers (MCA, GST, eCourts),
  never scraping or CAPTCHA bypass.

## Lines to stay behind

1. Never give buy/sell/hold calls, price targets or rankings of listed
   stocks.
2. Do not call output a "credit rating" or show grades like "AA / BBB";
   credit ratings are regulated. Show evidence and flags.
3. Do not act as a credit bureau or sell repayment histories (RBI-regulated).
4. Never write "this company is a fraud"; write "claim contradicted by
   [source]".
5. Follow the DPDP Act for director and individual data: minimal
   collection, privacy policy, correction requests.
6. Confirm the setup with a fintech lawyer before launch.

## Original 30-day plan

1. Week 1: interview about 15 SME owners, exporters and NBFC credit teams.
2. Week 2: build the database, worker and real LLM pieces on the counterparty
   check.
3. Week 3: generate and hand-check 20 real reports.
4. Week 4: free pilots with 5 businesses; charge from month 2.
