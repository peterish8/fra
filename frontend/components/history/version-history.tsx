"use client";
import { useState } from "react";

export type ReportVersionSummary = { version: number; createdAt: string; status: string; changeSummary?: string };
export function VersionHistory({ versions, onRefresh }: { versions: ReportVersionSummary[]; onRefresh?: () => Promise<void> }) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  async function refresh() { if (!onRefresh) return; setPending(true); setMessage("Refresh queued; the current version remains readable until publication."); try { await onRefresh(); setMessage("Refresh published as a new version."); } catch { setMessage("Refresh failed. The previous version is unchanged; retry when ready."); } finally { setPending(false); } }
  return <section aria-labelledby="history-title"><div style={{display:"flex",justifyContent:"space-between"}}><h2 id="history-title">Version history</h2><button type="button" disabled={pending || !onRefresh} onClick={() => void refresh()}>{pending ? "Refreshing…" : "Refresh report"}</button></div>{message ? <p role="status">{message}</p> : null}<ol>{versions.length ? versions.map((version) => <li key={version.version}><strong>Version {version.version}</strong> · {version.status} · {new Date(version.createdAt).toLocaleDateString()}<p>{version.changeSummary ?? "No recorded changes."}</p></li>) : <li>No prior versions yet.</li>}</ol></section>;
}
