"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

type ThesisState = "OPEN" | "SUPPORTED" | "WEAKENED" | "UNCHANGED";

type ThesisItem = {
  id: string;
  statement: string;
  falsifier: string;
  state: ThesisState;
  note: string;
};

const initialTheses: ThesisItem[] = [
  { id: "thesis-1", statement: "Demand for the current AI infrastructure cycle remains material through the next reported period.", falsifier: "Order commentary or independent channel evidence shows a sustained demand reversal.", state: "SUPPORTED", note: "Tracked separately from any single financial conclusion." },
  { id: "thesis-2", statement: "Margin expansion can persist without a material deterioration in working-capital quality.", falsifier: "Cash conversion weakens or receivables grow faster than comparable revenue.", state: "OPEN", note: "Requires period-aligned cash-flow evidence." },
];

const briefItems = [
  { direction: "UPDATED", title: "Separate reported results from management guidance", detail: "A guidance statement is a forecast, not a realized result. Keep it distinct before comparing periods.", source: "Investor presentation · fixture snapshot" },
  { direction: "NEW RISK", title: "Recheck scope and definition changes", detail: "A changed segment definition, currency treatment, or accounting basis can create an apparent value change.", source: "Filing comparison policy · fixture snapshot" },
  { direction: "OPEN", title: "Review analyst questions against the source record", detail: "Open questions remain visible until independent evidence or a documented limitation resolves them.", source: "Evidence ledger · fixture snapshot" },
];

function StatusPill({ status }: { status: ThesisState }) {
  const label = status === "SUPPORTED" ? "Supported" : status === "WEAKENED" ? "Weakened" : status === "UNCHANGED" ? "Unchanged" : "Open";
  return <span className={`analyst-status analyst-status-${status.toLowerCase()}`}>{label}</span>;
}

export function ThesisTrackerPage() {
  const [items, setItems] = useState(initialTheses);
  const [statement, setStatement] = useState("");
  const [falsifier, setFalsifier] = useState("");

  function addThesis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (statement.trim().length < 8 || falsifier.trim().length < 8) return;
    setItems((current) => [{ id: `thesis-${Date.now()}`, statement: statement.trim(), falsifier: falsifier.trim(), state: "OPEN", note: "Local draft — link it to claim evidence after the workspace is created." }, ...current]);
    setStatement("");
    setFalsifier("");
  }

  function advanceStatus(id: string) {
    const order: ThesisState[] = ["OPEN", "SUPPORTED", "WEAKENED", "UNCHANGED"];
    setItems((current) => current.map((item) => item.id === id ? { ...item, state: order[(order.indexOf(item.state) + 1) % order.length] } : item));
  }

  return <main className="analyst-page" id="main-content">
    <header className="analyst-topbar"><div className="discover-breadcrumb"><span>Research</span><i aria-hidden="true">/</i><strong>Thesis tracker</strong></div><span>Local draft mode</span></header>
    <div className="analyst-canvas">
      <section className="analyst-hero"><p>Thesis tracker</p><h1>Keep the question<br /><em>ahead of the conclusion.</em></h1><span>A thesis is a researcher-authored proposition with a condition that would change your mind. It is never a substitute for a claim verdict.</span></section>
      <section className="analyst-rule" aria-label="Thesis tracker principles"><div><b>1</b><p><strong>Write the proposition</strong>Make it specific enough to inspect.</p></div><div><b>2</b><p><strong>Name the falsifier</strong>State what evidence would weaken it.</p></div><div><b>3</b><p><strong>Link the record</strong>Attach sourced claim versions before relying on it.</p></div></section>
      <div className="analyst-grid">
        <section className="analyst-surface analyst-thesis-list" aria-labelledby="tracked-theses"><div className="analyst-heading"><div><p>Tracked propositions</p><h2 id="tracked-theses">Thesis ledger</h2></div><span>{items.length} points</span></div>{items.map((item) => <article key={item.id} className="analyst-thesis-item"><div className="analyst-thesis-top"><StatusPill status={item.state} /><button type="button" onClick={() => advanceStatus(item.id)}>Update status</button></div><h3>{item.statement}</h3><div><span>Falsifier</span><p>{item.falsifier}</p></div><small>{item.note}</small></article>)}</section>
        <aside className="analyst-surface analyst-thesis-form"><p>New thesis point</p><h2>What would you need to see?</h2><form onSubmit={addThesis}><label>Proposition<textarea value={statement} onChange={(event) => setStatement(event.target.value)} placeholder="What do you believe is likely to be true?" /></label><label>Falsifier<textarea value={falsifier} onChange={(event) => setFalsifier(event.target.value)} placeholder="What evidence would weaken this view?" /></label><button type="submit">Add to thesis ledger <span aria-hidden="true">→</span></button></form><small>Local drafts are clearly separated from verified report claims.</small></aside>
      </div>
    </div>
  </main>;
}

export function ChangeBriefPage() {
  const [kind, setKind] = useState<"Earnings" | "Filing">("Earnings");
  return <main className="analyst-page" id="main-content">
    <header className="analyst-topbar"><div className="discover-breadcrumb"><span>Research</span><i aria-hidden="true">/</i><strong>Change brief</strong></div><span>Source-linked fixture</span></header>
    <div className="analyst-canvas">
      <section className="analyst-hero analyst-brief-hero"><p>Change brief</p><h1>Read the delta.<br /><em>Keep the context.</em></h1><span>A concise review surface for earnings materials and filings. Every production line item must map to an evidence snapshot and, where relevant, a claim version.</span></section>
      <section className="analyst-brief-toolbar"><div><span>Brief type</span><button type="button" className={kind === "Earnings" ? "active" : ""} onClick={() => setKind("Earnings")}>Earnings</button><button type="button" className={kind === "Filing" ? "active" : ""} onClick={() => setKind("Filing")}>Filing</button></div><Link href="/tearsheet">Open cited tearsheet <span aria-hidden="true">→</span></Link></section>
      <section className="analyst-surface analyst-brief-sheet" aria-labelledby="brief-title"><div className="analyst-heading"><div><p>{kind} review</p><h2 id="brief-title">What changed, what it means, what remains open</h2></div><span>Fixture only</span></div>{briefItems.map((item) => <article className="analyst-brief-item" key={item.title}><div><span className={`analyst-direction analyst-direction-${item.direction.toLowerCase().replace(" ", "-")}`}>{item.direction}</span><h3>{item.title}</h3><p>{item.detail}</p></div><aside><span>Source</span><a href="#source-ledger">{item.source}</a><small>Retrieval timestamp retained in source ledger</small></aside></article>)}<footer id="source-ledger"><span aria-hidden="true">i</span> This is a local fixture presentation. Provider retrieval, live filing comparison, estimates, and price data are not running.</footer></section>
    </div>
  </main>;
}

export function TearsheetPage() {
  const [printed, setPrinted] = useState(false);
  function printSheet() { setPrinted(true); window.print(); }
  return <main className="analyst-page tearsheet-page" id="main-content">
    <header className="analyst-topbar no-print"><div className="discover-breadcrumb"><span>Reports</span><i aria-hidden="true">/</i><strong>Tearsheet</strong></div><button type="button" onClick={printSheet}>{printed ? "Print dialog opened" : "Print / save PDF"}</button></header>
    <div className="analyst-canvas">
      <article className="tearsheet" aria-labelledby="tearsheet-title"><header><div><p>Evidence-led research tearsheet</p><h1 id="tearsheet-title">NVIDIA<br /><em>Research posture</em></h1></div><span>Fixture view<br />03 Sep 2026</span></header><section className="tearsheet-lede"><p>This concise view is a cited research handoff, not a recommendation. It keeps facts, analyst questions, and limitations visible in the same place.</p><div><strong>Research mode</strong><span>Initiation</span></div><div><strong>Evidence posture</strong><span>Local fixture</span></div></section><section className="tearsheet-columns"><div><p>Research posture</p><h2>Evidence before explanation</h2><span>Company claims, independent evidence, and deterministic financial checks remain separate records. Any conclusion must remain traceable to those records.</span><a href="#citations">[1] Fixture report lineage</a></div><div><p>What changed</p><h2>Review the filing delta first</h2><span>Definitions, scope, periods, and accounting basis must be checked before a reported change is treated as a comparable financial result.</span><a href="#citations">[2] Fixture verification policy</a></div><div><p>Open question</p><h2>Does coverage support the thesis?</h2><span>Thesis status is not a verdict. Link the proposition to exact claim versions and independent source families before relying on it.</span><a href="#citations">[3] Fixture source ledger</a></div></section><footer id="citations"><div><strong>Sources & limitations</strong><span>[1]–[3] Fixture citations used for local UI validation. No live sources, prices, financial outputs, or provider retrieval have been used.</span></div><div>Research discovery, not investment advice.</div></footer></article>
    </div>
  </main>;
}
