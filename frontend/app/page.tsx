import Link from "next/link";

import { demoWatchlist } from "@/lib/demo-data";

function FoundationStatus() {
  return <div className="foundation-status" role="status"><span className="status-dot" aria-hidden="true" /><span>Foundation ready</span></div>;
}

export default function HomePage() {
  return (
    <main className="main-content" id="main-content">
      <header className="topbar"><div className="breadcrumb" aria-label="Breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><strong>Discover</strong></div><FoundationStatus /></header>
      <div className="content-frame">
        <section className="intro" aria-labelledby="page-title"><p className="section-kicker">Financial Research Agent</p><h1 id="page-title">What companies say. What the evidence says.</h1><p className="intro-copy">An evidence-first workspace for researching companies with clear provenance, explicit uncertainty, and reports you can inspect.</p></section>
        <section className="foundation-panel" aria-labelledby="foundation-title"><div className="panel-heading"><div><p className="panel-label">Workspace status</p><h2 id="foundation-title">Ready for your first research workspace</h2></div><span className="panel-status">No active research</span></div><div className="empty-state"><div className="empty-state-icon" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M6.5 7.5h13l6 6v11h-19z" /><path d="M19.5 7.75v6h6M10.5 18h11M10.5 22h7" /></svg></div><div className="empty-state-content"><h3>No research workspace yet</h3><p>Create a workspace to capture company statements, compare them with permitted independent evidence, and review the source trail.</p></div></div><div className="panel-note"><span className="note-icon" aria-hidden="true">i</span><p>This foundation shell does not load provider data or make research claims. Uncertainty will remain visible as the workspace grows.</p></div></section>
        <section className="demo-snapshot" aria-labelledby="snapshot-title"><div className="panel-heading"><div><p className="panel-label">Demo data · local only</p><h2 id="snapshot-title">Research watchlist snapshot</h2></div><Link className="text-link" href="/discover">Open Discover →</Link></div><div className="snapshot-grid">{demoWatchlist.slice(0, 3).map((entry) => <article className="snapshot-card" key={entry.company_id}><div><span className="snapshot-rank">#{entry.rank}</span><strong>{entry.name}</strong></div><span className={entry.score == null ? "snapshot-score snapshot-score-muted" : "snapshot-score"}>{entry.score == null ? "—" : `${entry.score}/100`}</span><p>{entry.explanation}</p><small>{entry.coverage}% evidence coverage · {entry.state?.replaceAll("_", " ")}</small></article>)}</div><div className="demo-links"><Link href="/reports">View sample report</Link><Link href="/compare">Compare companies</Link><Link href="/research">Open research workspace</Link></div></section>
        <footer className="page-footer"><span>Research discovery, not investment advice.</span><span>Phase 01 · Foundation</span></footer>
      </div>
    </main>
  );
}
