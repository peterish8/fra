"use client";
import { useMemo, useState } from "react";

export type ClaimRow = { id: string; text: string; origin: "Company" | "Independent"; materiality: string; verdict: string; confidence?: number; sourceFamily?: string };

export function ClaimsTable({ claims, onInspect }: { claims: ClaimRow[]; onInspect: (claim: ClaimRow) => void }) {
  const [filter, setFilter] = useState("ALL");
  const visible = useMemo(() => filter === "ALL" ? claims : claims.filter((claim) => claim.verdict === filter), [claims, filter]);
  return <section className="claims-panel" aria-labelledby="claims-title"><div className="claims-panel-heading"><h2 id="claims-title">Claims and evidence</h2><label>Filter <select value={filter} onChange={(event) => setFilter(event.target.value)}><option>ALL</option><option>VERIFIED</option><option>PARTIALLY_SUPPORTED</option><option>UNVERIFIED</option><option>CONTRADICTED</option></select></label></div><div className="claims-table-wrap"><table><thead><tr><th>Claim</th><th>Origin</th><th>Materiality</th><th>Outcome</th><th>Confidence</th><th /></tr></thead><tbody>{visible.map((claim) => <tr key={claim.id}><td>{claim.text}</td><td>{claim.origin}</td><td>{claim.materiality}</td><td>{claim.verdict}</td><td>{claim.confidence == null ? "Not enough data" : `${claim.confidence}/100`}</td><td><button type="button" onClick={() => onInspect(claim)}>Inspect evidence</button></td></tr>)}</tbody></table></div>{visible.length === 0 ? <p role="status">No claims match this filter.</p> : null}</section>;
}
