import Link from "next/link";

import { demoWatchlist } from "@/lib/demo-data";

type NavigationItem = {
  label: string;
  href: string;
  icon: "discover" | "research" | "compare" | "settings";
  current?: boolean;
};

const navigationItems: NavigationItem[] = [
  { label: "Discover", href: "/", icon: "discover", current: true },
  { label: "My Research", href: "/research", icon: "research" },
  { label: "Compare", href: "/compare", icon: "compare" },
  { label: "Settings", href: "/", icon: "settings" },
];

function NavigationIcon({ name }: { name: NavigationItem["icon"] }) {
  if (name === "discover") {
    return (
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
        <circle cx="9" cy="9" r="5.5" />
        <path d="m13.25 13.25 3.5 3.5" />
      </svg>
    );
  }

  if (name === "research") {
    return (
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
        <path d="M4.5 3.5h7.25l3.75 3.75V16.5h-11z" />
        <path d="M11.5 3.75V7.5h3.75M7 10h6M7 13h4" />
      </svg>
    );
  }

  if (name === "compare") {
    return (
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
        <path d="M4 5.5h7M4 10h12M4 14.5h7" />
        <path d="m12.5 4 3 1.5-3 1.5M7.5 13l-3 1.5 3 1.5" />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
      <path d="M10 3.25a2 2 0 0 1 1.95 1.55l.15.63a5.6 5.6 0 0 1 1.03.6l.62-.2a2 2 0 0 1 2.43.9l.22.38a2 2 0 0 1-.48 2.54l-.48.4c.04.28.06.58.06.87s-.02.59-.06.87l.48.4a2 2 0 0 1 .48 2.54l-.22.38a2 2 0 0 1-2.43.9l-.62-.2a5.6 5.6 0 0 1-1.03.6l-.15.63A2 2 0 0 1 10 16.75h-.44a2 2 0 0 1-1.95-1.55l-.15-.63a5.6 5.6 0 0 1-1.03-.6l-.62.2a2 2 0 0 1-2.43-.9l-.22-.38a2 2 0 0 1 .48-2.54l.48-.4A5.9 5.9 0 0 1 4.06 9l-.48-.4a2 2 0 0 1-.48-2.54l.22-.38a2 2 0 0 1 2.43-.9l.62.2a5.6 5.6 0 0 1 1.03-.6l.15-.63A2 2 0 0 1 9.56 3.25z" />
      <circle cx="9.78" cy="10" r="2.1" />
    </svg>
  );
}

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}

function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Research workspace sidebar">
      <div className="sidebar-top">
        <Link className="brand" href="/" aria-label="Financial Research Agent home">
          <BrandMark />
          <span>Financial Research</span>
        </Link>

        <nav className="primary-nav" aria-label="Primary navigation">
          {navigationItems.map((item) => (
            <a
              className={`nav-item${item.current ? " nav-item-current" : ""}`}
              href={item.href}
              aria-current={item.current ? "page" : undefined}
              key={item.label}
            >
              <NavigationIcon name={item.icon} />
              <span>{item.label}</span>
            </a>
          ))}
        </nav>
      </div>

      <div className="sidebar-bottom">
        <div className="sidebar-section-heading">
          <span>My research</span>
          <span className="sidebar-count" aria-label="No research workspaces">
            0
          </span>
        </div>
        <p className="sidebar-empty">Your saved workspaces will appear here.</p>
        <div className="sidebar-rule" />
        <p className="sidebar-footnote">Evidence before explanation.</p>
      </div>
    </aside>
  );
}

function FoundationStatus() {
  return (
    <div className="foundation-status" role="status">
      <span className="status-dot" aria-hidden="true" />
      <span>Foundation ready</span>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <Sidebar />

      <main className="main-content" id="main-content">
        <header className="topbar">
          <div className="breadcrumb" aria-label="Breadcrumb">
            <span>Workspace</span>
            <span aria-hidden="true">/</span>
            <strong>Discover</strong>
          </div>
          <FoundationStatus />
        </header>

        <div className="content-frame">
          <section className="intro" aria-labelledby="page-title">
            <p className="section-kicker">Financial Research Agent</p>
            <h1 id="page-title">What companies say. What the evidence says.</h1>
            <p className="intro-copy">
              An evidence-first workspace for researching companies with clear
              provenance, explicit uncertainty, and reports you can inspect.
            </p>
          </section>

          <section className="foundation-panel" aria-labelledby="foundation-title">
            <div className="panel-heading">
              <div>
                <p className="panel-label">Workspace status</p>
                <h2 id="foundation-title">Ready for your first research workspace</h2>
              </div>
              <span className="panel-status">No active research</span>
            </div>

            <div className="empty-state">
              <div className="empty-state-icon" aria-hidden="true">
                <svg viewBox="0 0 32 32" fill="none">
                  <path d="M6.5 7.5h13l6 6v11h-19z" />
                  <path d="M19.5 7.75v6h6M10.5 18h11M10.5 22h7" />
                </svg>
              </div>
              <div className="empty-state-content">
                <h3>No research workspace yet</h3>
                <p>
                  Create a workspace to capture company statements, compare them
                  with permitted independent evidence, and review the source trail.
                </p>
              </div>
            </div>

            <div className="panel-note">
              <span className="note-icon" aria-hidden="true">i</span>
              <p>
                This foundation shell does not load provider data or make research
                claims. Uncertainty will remain visible as the workspace grows.
              </p>
            </div>
          </section>

          <section className="demo-snapshot" aria-labelledby="snapshot-title">
            <div className="panel-heading">
              <div><p className="panel-label">Demo data · local only</p><h2 id="snapshot-title">Research watchlist snapshot</h2></div>
              <Link className="text-link" href="/discover">Open Discover →</Link>
            </div>
            <div className="snapshot-grid">
              {demoWatchlist.slice(0, 3).map((entry) => (
                <article className="snapshot-card" key={entry.company_id}>
                  <div><span className="snapshot-rank">#{entry.rank}</span><strong>{entry.name}</strong></div>
                  <span className={entry.score == null ? "snapshot-score snapshot-score-muted" : "snapshot-score"}>{entry.score == null ? "—" : `${entry.score}/100`}</span>
                  <p>{entry.explanation}</p>
                  <small>{entry.coverage}% evidence coverage · {entry.state?.replaceAll("_", " ")}</small>
                </article>
              ))}
            </div>
            <div className="demo-links"><Link href="/reports">View sample report</Link><Link href="/compare">Compare companies</Link><Link href="/research">Open research workspace</Link></div>
          </section>

          <footer className="page-footer">
            <span>Research discovery, not investment advice.</span>
            <span>Phase 01 · Foundation</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
