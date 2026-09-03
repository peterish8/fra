"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import { demoWatchlist } from "@/lib/demo-data";

type Filter = "All" | "Public" | "Needs review";
type DeskMode = "INITIATION" | "EARNINGS" | "UPDATE" | "DILIGENCE";

const deskModes: Array<{ value: DeskMode; label: string; prompt: string }> = [
  { value: "INITIATION", label: "Initiation", prompt: "Build the first evidence-led view of this company." },
  { value: "EARNINGS", label: "Earnings", prompt: "Latest results versus the comparable period and prior guidance." },
  { value: "UPDATE", label: "Update", prompt: "What changed since the last report version?" },
  { value: "DILIGENCE", label: "Diligence", prompt: "Test a specific question, risk, or thesis condition." },
];

function EvidenceMeter({ value }: { value: number }) {
  return <div className="desk-meter" aria-label={`${value}% evidence coverage`}><span style={{ width: `${value}%` }} /><b>{value}%</b></div>;
}

function RankSignal({ value }: { value: number | null }) {
  if (value == null) return <span className="desk-rank desk-rank-neutral">No change</span>;
  return <span className={`desk-rank ${value > 0 ? "desk-rank-up" : "desk-rank-down"}`}>{value > 0 ? `Up ${value}` : `Down ${Math.abs(value)}`}</span>;
}

export function DiscoverHome() {
  const router = useRouter();
  const [ticker, setTicker] = useState("");
  const [company, setCompany] = useState("");
  const [brief, setBrief] = useState("");
  const [mode, setMode] = useState<DeskMode>("INITIATION");
  const [filter, setFilter] = useState<Filter>("All");

  const selectedMode = deskModes.find((item) => item.value === mode) ?? deskModes[0];
  const entries = useMemo(() => demoWatchlist.filter((entry) => {
    if (filter === "Public") return entry.cohort === "PUBLIC";
    if (filter === "Needs review") return entry.state !== "ELIGIBLE";
    return true;
  }), [filter]);

  function openWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const subject = company.trim() || ticker.trim();
    const params = new URLSearchParams({ mode });
    if (subject) params.set("company", subject);
    if (ticker.trim()) params.set("ticker", ticker.trim().toUpperCase());
    if (brief.trim()) params.set("brief", brief.trim());
    router.push(`/research?${params.toString()}`);
  }

  return (
    <main className="desk-page" id="main-content">
      <header className="desk-topbar">
        <div className="desk-breadcrumb"><span>Workspace</span><i aria-hidden="true">/</i><b>Discover</b></div>
        <p><span aria-hidden="true" />Local preview · sources and uncertainty remain visible</p>
      </header>

      <div className="desk-canvas">
        <section className="desk-command-panel" aria-labelledby="desk-title">
          <div className="desk-command-heading">
            <p>New research</p>
            <h1 id="desk-title">Open a research workspace</h1>
            <span>Choose the company, frame the question, and keep every conclusion connected to its record.</span>
          </div>

          <form onSubmit={openWorkspace}>
            <div className="desk-mode-list" aria-label="Research mode">
              {deskModes.map((item) => <button key={item.value} className={mode === item.value ? "desk-mode-active" : ""} type="button" onClick={() => setMode(item.value)}>{item.label}</button>)}
            </div>
            <p className="desk-mode-prompt">{selectedMode.prompt}</p>

            <div className="desk-subject-grid">
              <label><span>Ticker <i>Optional</i></span><input value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="NVDA" autoCapitalize="characters" /></label>
              <label><span>Company</span><input value={company} onChange={(event) => setCompany(event.target.value)} placeholder="NVIDIA" autoComplete="organization" /></label>
            </div>
            <label className="desk-brief-field"><span>Research brief</span><textarea value={brief} onChange={(event) => setBrief(event.target.value)} rows={3} placeholder="What should this research answer? A thesis, event, comparison, or diligence question is enough." /></label>
            <div className="desk-command-actions">
              <button type="submit" className="desk-run-button"><span aria-hidden="true">⌕</span> Open research workspace</button>
              <Link href="/research">Browse saved workspaces <span aria-hidden="true">→</span></Link>
            </div>
          </form>
          <div className="desk-suggestions" aria-label="Example research prompts">
            <span>Examples</span>
            <button type="button" onClick={() => { setTicker("HDFCBANK"); setCompany("HDFC Bank"); setMode("EARNINGS"); }}>HDFC Bank earnings</button>
            <button type="button" onClick={() => { setTicker("DIXON"); setCompany("Dixon Technologies"); setMode("INITIATION"); }}>Dixon initiation</button>
            <button type="button" onClick={() => { setTicker("NVDA"); setCompany("NVIDIA"); setMode("UPDATE"); }}>NVIDIA update</button>
          </div>
        </section>

        <section className="desk-watchlist" aria-labelledby="watchlist-title">
          <div className="desk-section-heading">
            <div><p>Your coverage</p><h2 id="watchlist-title">Research watchlist</h2></div>
            <div className="desk-filter-list" aria-label="Watchlist filters">
              {(["All", "Public", "Needs review"] as Filter[]).map((item) => <button key={item} className={filter === item ? "desk-filter-active" : ""} type="button" onClick={() => setFilter(item)}>{item}</button>)}
            </div>
          </div>
          <p className="desk-section-copy">A sample priority queue for research coverage—not a stock ranking or recommendation. Score and coverage remain explainable.</p>
          <div className="desk-watchlist-table" role="region" aria-label="Research watchlist table" tabIndex={0}>
            <div className="desk-table-head" aria-hidden="true"><span>Rank</span><span>Company and research posture</span><span>Evidence coverage</span><span>Research confidence</span><span>Movement</span></div>
            {entries.map((entry) => {
              const companyName = entry.name ?? "Unnamed company";
              return <article className="desk-row" key={entry.company_id}>
                <span className="desk-row-rank">{String(entry.rank).padStart(2, "0")}</span>
                <div className="desk-company"><span className="desk-company-ticker">{companyName.slice(0, 4).toUpperCase()}</span><div><strong>{companyName}</strong><small>{entry.cohort === "PUBLIC" ? "Public company" : "Private company"} · {entry.state === "ELIGIBLE" ? "Coverage eligible" : "Coverage incomplete"}</small><p>{entry.explanation}</p></div></div>
                <EvidenceMeter value={entry.coverage ?? 0} />
                <div className="desk-score"><strong>{entry.score == null ? "—" : entry.score}</strong><span>{entry.score == null ? "Insufficient evidence" : "Explained score"}</span></div>
                <RankSignal value={entry.rank_delta ?? null} />
              </article>;
            })}
          </div>
          <footer className="desk-watchlist-footer"><span><i aria-hidden="true">i</i> Fixture data only. Live provider retrieval is not enabled in this local environment.</span><Link href="/discover">Methodology and coverage <span aria-hidden="true">→</span></Link></footer>
        </section>
      </div>
    </main>
  );
}
