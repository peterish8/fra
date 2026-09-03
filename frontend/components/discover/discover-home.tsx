"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import { demoWatchlist } from "@/lib/demo-data";

type Filter = "All" | "Public" | "Needs review";

const focusAreas = ["Financial health", "Growth", "Risk signals", "Disclosure quality"];

function EvidenceMeter({ value }: { value: number }) {
  return <div className="discover-meter" aria-label={`${value}% evidence coverage`}><span style={{ width: `${value}%` }} /><b>{value}%</b></div>;
}

function RankSignal({ value }: { value: number | null }) {
  if (value == null) return <span className="discover-rank-neutral">—</span>;
  return <span className={value > 0 ? "discover-rank-up" : "discover-rank-down"}>{value > 0 ? `↑ ${value}` : `↓ ${Math.abs(value)}`}</span>;
}

export function DiscoverHome() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [focus, setFocus] = useState("Financial health");
  const [filter, setFilter] = useState<Filter>("All");

  const entries = useMemo(() => demoWatchlist.filter((entry) => {
    if (filter === "Public") return entry.cohort === "PUBLIC";
    if (filter === "Needs review") return entry.state !== "ELIGIBLE";
    return true;
  }), [filter]);

  function openWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const company = query.trim();
    router.push(company ? `/research?company=${encodeURIComponent(company)}` : "/research");
  }

  return (
    <main className="discover-page" id="main-content">
      <header className="discover-topbar">
        <div className="discover-breadcrumb" aria-label="Breadcrumb"><span>Workspace</span><i aria-hidden="true">/</i><strong>Discover</strong></div>
        <div className="discover-runtime"><span aria-hidden="true" /><span>Local research environment</span></div>
      </header>

      <div className="discover-canvas">
        <section className="discover-hero" aria-labelledby="discover-title">
          <div className="discover-hero-copy">
            <p className="discover-eyebrow"><span aria-hidden="true" /> Evidence-led company research</p>
            <h1 id="discover-title">Follow the claim.<br /><em>Inspect the record.</em></h1>
            <p>Build a defensible view of a company from its own disclosures, independent evidence, and reconciled financial facts.</p>
          </div>

          <form className="discover-command" onSubmit={openWorkspace}>
            <label htmlFor="company-query">Start a research workspace</label>
            <div className="discover-command-row">
              <span className="discover-search-icon" aria-hidden="true">⌕</span>
              <input id="company-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Company, ticker, or domain" autoComplete="off" />
              <button type="submit">Open workspace <span aria-hidden="true">→</span></button>
            </div>
            <div className="discover-focus-row" aria-label="Research focus">
              <span>Focus</span>
              {focusAreas.map((area) => <button key={area} className={focus === area ? "discover-focus-active" : ""} type="button" onClick={() => setFocus(area)}>{area}</button>)}
            </div>
          </form>

          <div className="discover-hero-notes">
            <div><span>01</span><p><b>Claim-aware</b>Company statements remain distinct from independent evidence.</p></div>
            <div><span>02</span><p><b>Traceable</b>Every report remains anchored to the sources behind it.</p></div>
            <div><span>03</span><p><b>Honest by default</b>Missing data stays visible as missing data.</p></div>
          </div>
        </section>

        <section className="discover-brief" aria-label="Research environment summary">
          <div><span>Current methodology</span><strong>Evidence ledger <b>v1.0</b></strong></div>
          <div><span>Public watchlist</span><strong>4 <b>tracked companies</b></strong></div>
          <div><span>Last local refresh</span><strong>Today <b>· fixture data</b></strong></div>
          <Link href="/research">View research queue <span aria-hidden="true">↗</span></Link>
        </section>

        <section className="discover-watchlist" aria-labelledby="watchlist-title">
          <div className="discover-section-heading">
            <div><p>Research watchlist</p><h2 id="watchlist-title">Signals worth inspecting</h2></div>
            <div className="discover-filter-list" aria-label="Watchlist filters">
              {(["All", "Public", "Needs review"] as Filter[]).map((item) => <button key={item} className={filter === item ? "discover-filter-active" : ""} type="button" onClick={() => setFilter(item)}>{item}</button>)}
            </div>
          </div>
          <p className="discover-section-copy">A research prioritization view, not a recommendation list. Scores explain evidence quality and availability — never investment merit.</p>

          <div className="discover-watchlist-table" role="region" aria-label="Research watchlist table" tabIndex={0}>
            <div className="discover-table-head" aria-hidden="true"><span>Rank</span><span>Company / research reading</span><span>Evidence coverage</span><span>Research confidence</span><span>Movement</span></div>
            {entries.map((entry) => {
              const companyName = entry.name ?? "Unnamed company";
              return <article className="discover-row" key={entry.company_id}>
                <span className="discover-row-rank">{String(entry.rank).padStart(2, "0")}</span>
                <div className="discover-company"><div className="discover-monogram" aria-hidden="true">{companyName.slice(0, 1)}</div><div><strong>{companyName}</strong><small>{entry.cohort === "PUBLIC" ? "Public company" : "Private company"} · {entry.state === "ELIGIBLE" ? "Evidence eligible" : "Coverage incomplete"}</small><p>{entry.explanation}</p></div></div>
                <EvidenceMeter value={entry.coverage ?? 0} />
                <div className="discover-score"><strong>{entry.score == null ? "—" : entry.score}</strong><span>{entry.score == null ? "Insufficient evidence" : "Explained score"}</span></div>
                <RankSignal value={entry.rank_delta ?? null} />
              </article>;
            })}
          </div>
          <footer className="discover-watchlist-footer"><span><i aria-hidden="true">i</i> Demo fixture data · provider retrieval is not running in this local environment.</span><Link href="/discover">Open detailed watchlist <span aria-hidden="true">→</span></Link></footer>
        </section>

        <footer className="discover-footer"><span>Evidence before explanation.</span><span>Research discovery, not investment advice.</span></footer>
      </div>
    </main>
  );
}
