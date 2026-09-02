"use client";
import { useState } from "react";
import { ClaimsTable, type ClaimRow } from "../claims/claims-table";
import { EvidenceInspector } from "../evidence/evidence-inspector";

const sampleClaims: ClaimRow[] = [
  { id: "claim-1", text: "The company reported positive operating cash flow.", origin: "Company", materiality: "HIGH", verdict: "PARTIALLY_SUPPORTED", confidence: 72, sourceFamily: "Regulatory filing" },
  { id: "claim-2", text: "Independent sources describe the product launch timing.", origin: "Independent", materiality: "MEDIUM", verdict: "VERIFIED", confidence: 91, sourceFamily: "Independent journalism" },
];

function ScoreCard({ label, score, coverage, version, explanation }: { label: string; score: string; coverage: string; version: string; explanation: string }) {
  return <article style={{border:"1px solid #ccd",padding:16}}><h3>{label}</h3><p style={{fontSize:24}}>{score}</p><p>Coverage: {coverage}</p><small>{version} · {explanation}</small></article>;
}

export function ReportReader({ claims = sampleClaims }: { claims?: ClaimRow[] }) {
  const [selected, setSelected] = useState<ClaimRow | null>(null);
  return <main><header><p>Report reader</p><h1>Evidence-led company report</h1><p>Separate what the company said from what independent evidence supports. Scores explain quality; they do not decide truth.</p></header><section aria-label="Report quality" style={{display:"grid",gridTemplateColumns:"repeat(4,minmax(0,1fr))",gap:12}}><ScoreCard label="Research Confidence" score="78/100" coverage="82%" version="research-confidence-v1" explanation="Weighted claim quality and evidence coverage." /><ScoreCard label="Evidence Coverage" score="82/100" coverage="82%" version="evidence-coverage-v1" explanation="Materiality-weighted assessed claims." /><ScoreCard label="Disclosure Reliability" score="Not enough data" coverage="34%" version="disclosure-reliability-v1" explanation="Independent sample gate is not met." /><ScoreCard label="Financial/Business Score" score="64/100" coverage="68%" version="financial-business-v1" explanation="Cohort-normalized components." /></section><nav aria-label="Report sections"><a href="#overview">Overview</a> · <a href="#financials">Financials</a> · <a href="#claims">Claims</a> · <a href="#sources">Sources</a> · <a href="#limitations">Limitations</a></nav><section id="overview"><h2>Overview</h2><p>Identity and report scope are resolved. Unverified and stale statements remain visible rather than being silently promoted.</p></section><div id="claims"><ClaimsTable claims={claims} onInspect={setSelected} /></div><EvidenceInspector claim={selected} onClose={() => setSelected(null)} /><section id="limitations"><h2>Limitations</h2><p>Some sources may be unavailable or stale. Missing data is shown as unknown, never as zero.</p></section></main>;
}
