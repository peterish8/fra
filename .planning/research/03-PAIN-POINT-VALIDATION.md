# Pain-point validation (2026-10-07)

Checks the counterparty-check idea from `02-PIVOT-OPTIONS.md` against market
data and competitors. Verdict: **the pain is real, but a plain company-data
report is already a commodity.** The opportunity is narrower and different.

Sources are listed at the end. Figures come from news and vendor pages found
by web search; re-check them before using them in a pitch.

## 1. Is the pain real? Yes

| Pain | Evidence |
|---|---|
| Unpaid invoices | Delayed payments to MSMEs estimated at **₹7.34 lakh crore** as of March 2024 [1]. Recordent's study of about 1.1 lakh MSMEs: invoices take **73 days on average** to be paid [2]. |
| Disputes over unpaid bills | MSME Samadhaan (government late-payment portal): **about 2.57 lakh applications worth ₹55,244 crore** [3]. |
| Fake companies | **24,109 fake-invoice cases worth ₹41,664 crore** detected in FY26 up to October 2025 [4]; one case involved 3,558 fake companies [5]. |
| Fake buyers scamming exporters | Delhi Police arrested 18 people who posed as foreign buyers to cheat exporters [6]. Fake buyers remain a known risk on first deals [7]. |

## 2. Where the earlier plan was wrong

### A ₹499 company report already exists at that price

- Probe42: ₹499 for one company, down to ₹329 each in bulk, from 740+ sources
  [8].
- Tofler and Zaubacorp turn MCA filings into company profiles; Zauba is free
  to browse [9].
- Karza/Perfios and Signzy sell MCA and GSTIN verification APIs to lenders
  [10][11].
- ClearTax scores suppliers on GST filing compliance [12].

Collecting company data and printing a report is a commodity; competing on
price with funded incumbents is a losing plan.

### A check cannot fix the biggest cause of late payment

Nearly **40%** of delayed payments are owed by government departments and
PSUs [13], and an SME cannot refuse a big buyer. Checks only help with
**new or unknown** buyers.

### Data access is harder than implied

- **MCA:** no public API or bulk download; commercial "MCA APIs" are
  third-party resellers, and the portal's terms reportedly ban scraping
  [14].
- **GST:** taxpayer lookups go through licensed GST Suvidha Providers (GSPs),
  from about ₹0.50 per call [15][16].
- **Courts:** eCourts has no official API; data comes via resellers such as
  Surepass [17].

Every report carries data cost. Price with that in mind.

### Many small buyers are not on MCA

Sole proprietors and partnerships do not file with MCA; the GSTIN is often
the only public identifier.

## 3. Where the gap is

Incumbents answer **"show me data about company X."** No product found in
this research answers **"this person is offering me an order — is what they
say true, and what terms should I accept?"** That is the question the `fra`
claim-vs-evidence engine was designed for. Incumbents sell long data reports
that need a CA to interpret; this product sells a **decision**.

### Wedge A (top pick): exporters checking foreign buyers

- **Pain:** fake buyers and advance-fee scams (section 1).
- **Gap:** Probe42's export product verifies *Indian* companies for foreign
  buyers [18]. Indian exporters checking *foreign* buyers is less served.
  No dedicated tool was found, though this was a few searches, not an
  exhaustive scan.
- **Existing code:** GLEIF and UK Companies House adapters already exist in
  `backend/app/providers/registries/`.

### Wedge B: monitoring existing customers

Upload the debtor list (for example exported from Tally). The agent watches
every customer for warning signs: cancelled or suspended GST registration,
missed GST returns, new court cases, new lender charges. Reuses living
reports and `sources/freshness.py`.

ClearTax's check watches **suppliers** to protect input tax credit; this
watches **customers** to protect receivables.

## 4. How it works (Wedge A)

**Input:** the exporter forwards the buyer's email or purchase-order PDF by
email or WhatsApp.

1. **Extract claims (LLM).** Pull out what the buyer says about itself:
   name, country, year established, VAT number, size, email domain, phone,
   bank country, payment terms. Uses the existing `ExtractedClaim` schema.
2. **Resolve the entity (code).** Match against GLEIF, the national company
   register and OpenCorporates. `companies/resolver.py` asks the user when
   a match is uncertain instead of guessing.
3. **Check each claim (APIs + deterministic code).**
   - VAT number exists? EU **VIES** is free.
   - Email domain age via WHOIS: a free mail address or a weeks-old domain
     is a strong red flag.
   - Registered company matches the email signature?
   - Bank country differs from company country?
   - Web search for the name plus "scam" or "fraud".
4. **Judge the evidence (LLM + code).** Each claim is verified, partly
   verified, contradicted or unverified (`verification/`, `conflicts.py`).
   "Unverified" is never shown as "fake".
5. **Actionable output.** Three lines plus evidence, for example: "Company
   exists; 2 of 5 claims verified. ⚠️ Domain registered 3 weeks ago; bank
   account in a different country. **Suggested first-order terms: 100%
   advance or a letter of credit, no open credit.**" Every line links to a
   source.

Suggesting payment terms is a business suggestion, not a credit rating or
investment advice.

**Limits to state in the product:** it cannot guarantee someone is not a
fraud and cannot make government buyers pay. Unknowns stay marked unknown.

## 5. Validate before building

1. Interview 15–20 exporters via export councils or associations: "How did
   you check your last new overseas buyer? Have you ever been scammed?"
2. Hand-make 10 reports from real buyer emails they share. Asking "can I get
   this for every new buyer?" is the signal.
3. Landing page with a price (for example ₹299 per check or ₹2,999/month);
   count sign-ups before writing more code.

## Sources

1. [Storyboard18 — Delayed payments to MSMEs fall to Rs 7.34 lakh crore](https://storyboard18.com/how-it-works/delayed-payments-to-msmes-fall-to-rs-7-34-lakh-crore-report-84822.htm)
2. [MediaBrief — Recordent report: MSMEs wait 73 days on average](https://mediabrief.com/recordent-report-highlights-working-capital-stress-for-indian-smes-as-average-overdue-receivables-cross-%E2%82%B93-83-crore/)
3. [CRISIL — MSME bill and delayed payments](https://intelligence.crisil.com/en/homepage/newsroom/press-releases/2026/08/executed-well-msme-bill-can-be-an-ibc-moment-for-delayed-payments.html)
4. [TaxScan — GST evasion by fake companies](https://www.taxscan.in/?p=454186)
5. [Patrika — 3,000+ shell companies exposed](https://develop.patrika.com/en/national-news/fake-gst-bills-over-3000-shell-companies-exposed-%e2%82%b915000-crore-gst-loss-19794590)
6. [Asianet — Delhi Police bust fake call centre cheating exporters](https://newsable.asianetnews.com/india/delhi-police-bust-fake-call-centre-cheating-exporters-18-arrested-articleshow-gv4mgox)
7. [Apparel Resources — fake buyer warning](https://apparelresources.com/business-news/retail/beware-miguel-of-concora-special-barcelona-is-a-fake-buyer/)
8. [Probe42 — guide to company information in India](https://resources.probe42.in/probe-perspectives/business-intelligence/company-financial-information-india-complete-guide/)
9. [companydata.com — India B2B data provider comparison](https://companydata.com/b2b-data-provider-comparisons/india/)
10. [Signzy — fintech APIs](https://www.signzy.com/fintech-api)
11. [Perfios — top KYC API providers in India](https://perfios.ai/resources/blogs/top-kyc-api-providers-in-india/)
12. [ClearTax — vendor compliance risk](https://cleartax.in/s/vendor-compliance-risk)
13. [Swarajya — MSMEs waiting on government buyers](https://swarajyamag.com/amp/story/economy/beyond-gem-portal-why-msmes-are-still-waiting-for-their-money-from-government-buyers)
14. [companydata.com — MCA API](https://companydata.com/mca-api/)
15. [Vayana GSP — searchTaxpayer API](https://docs.gsp.vayana.com/GSTN/searchTaxpayer-get-api/)
16. [GSTZen — GST validator API pricing](https://gstzen.in/gst-validator-api-pricing-details)
17. [Surepass — eCourts API](https://surepass.io/ecourts-api/)
18. [Probe42 — verify Indian companies before you ship](https://campaigns.probe42.in/lp/foreign_business_export/)
