"use client";
import type { ClaimRow } from "../claims/claims-table";

export function EvidenceInspector({ claim, onClose }: { claim: ClaimRow | null; onClose: () => void }) {
  if (!claim) return null;
  return <aside role="dialog" aria-modal="true" aria-labelledby="evidence-title" style={{border:"1px solid #ccd",padding:16,marginTop:16}}><button type="button" onClick={onClose} aria-label="Close evidence inspector">Close</button><h2 id="evidence-title">Evidence inspector</h2><p><strong>{claim.text}</strong></p><dl><dt>Origin</dt><dd>{claim.origin}</dd><dt>Verdict</dt><dd>{claim.verdict}</dd><dt>Source family</dt><dd>{claim.sourceFamily ?? "Not available"}</dd></dl><p>Evidence excerpts, numeric checks, period checks, conflicts, and history are shown here when the report API provides them.</p></aside>;
}
