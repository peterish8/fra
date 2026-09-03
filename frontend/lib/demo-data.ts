import type { ClaimRow } from "@/components/claims/claims-table";
import type { ComparisonMetric } from "@/components/comparison/comparison-table";
import type { DiscoverItem } from "@/components/discover/discover-list";
import type { WatchlistEntry } from "@/components/watchlist/watchlist-table";

export const demoWatchlist: WatchlistEntry[] = [
  { company_id: "nvidia", name: "NVIDIA", cohort: "PUBLIC", rank: 1, score: 92, coverage: 88, rank_delta: 2, explanation: "Strong filing coverage and consistent independent confirmation.", state: "ELIGIBLE" },
  { company_id: "shopify", name: "Shopify", cohort: "PUBLIC", rank: 2, score: 86, coverage: 79, rank_delta: 1, explanation: "Growth claims align with reported operating metrics; margin definitions remain open.", state: "ELIGIBLE" },
  { company_id: "stripe", name: "Stripe", cohort: "PRIVATE", rank: 3, score: null, coverage: 54, rank_delta: null, explanation: "Interesting evidence, but private-company financial coverage is incomplete.", state: "INSUFFICIENT_COVERAGE" },
  { company_id: "adobe", name: "Adobe", cohort: "PUBLIC", rank: 4, score: 81, coverage: 84, rank_delta: -1, explanation: "Stable disclosure record with a recent product-transition question to investigate.", state: "ELIGIBLE" },
];

export const demoDiscover: DiscoverItem[] = [
  { company_id: "nvidia", name: "NVIDIA", score: 92, explanation: "High-quality public evidence across filings, product disclosures, and independent reporting.", state: "ELIGIBLE" },
  { company_id: "shopify", name: "Shopify", score: 86, explanation: "Strong growth evidence with one unresolved definition around operating margin.", state: "ELIGIBLE" },
  { company_id: "stripe", name: "Stripe", score: null, explanation: "The evidence trail is promising, but the available financial sample is not sufficient for a score.", state: "INSUFFICIENT_COVERAGE" },
];

export const demoComparisonMetrics: ComparisonMetric[] = [
  { metric: "Revenue growth", compatible: true, values: [{ company_id: "nvidia", value: "122%", claim_version_id: "claim-nvidia-growth" }, { company_id: "shopify", value: "26%", claim_version_id: "claim-shopify-growth" }, { company_id: "adobe", value: "11%", claim_version_id: "claim-adobe-growth" }] },
  { metric: "Research confidence", compatible: true, values: [{ company_id: "nvidia", value: "92/100" }, { company_id: "shopify", value: "86/100" }, { company_id: "adobe", value: "81/100" }] },
  { metric: "Disclosure reliability", compatible: false, warning: "COHORT_SCOPE_MIXED", values: [{ company_id: "nvidia", value: "High" }, { company_id: "shopify", value: "Medium" }, { company_id: "adobe", value: "High" }] },
  { metric: "Latest reported period", compatible: true, values: [{ company_id: "nvidia", value: "FY2025" }, { company_id: "shopify", value: "FY2025" }, { company_id: "adobe", value: "FY2024" }] },
];

export const demoClaims: ClaimRow[] = [
  { id: "claim-1", text: "The company reported positive operating cash flow in the latest fiscal year.", origin: "Company", materiality: "HIGH", verdict: "VERIFIED", confidence: 94, sourceFamily: "SEC filing" },
  { id: "claim-2", text: "Independent sources describe demand for the current product cycle as accelerating.", origin: "Independent", materiality: "HIGH", verdict: "PARTIALLY_SUPPORTED", confidence: 72, sourceFamily: "Independent journalism" },
  { id: "claim-3", text: "The company is the clear market leader in its category.", origin: "Company", materiality: "MEDIUM", verdict: "INSUFFICIENT_EVIDENCE", confidence: 38, sourceFamily: "Company website" },
  { id: "claim-4", text: "Reported revenue grew year over year during FY2025.", origin: "Independent", materiality: "HIGH", verdict: "VERIFIED", confidence: 98, sourceFamily: "SEC filing" },
];

