"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useDevSession } from "@/components/dev/dev-auth-gate";
import sessionStyles from "./local-session.module.css";

type IconName = "discover" | "research" | "reports" | "compare" | "thesis" | "brief" | "settings" | "admin";
type NavItem = { label: string; href: string; icon: IconName };

const navGroups: Array<{ label: string; items: NavItem[] }> = [
  { label: "Workspace", items: [{ label: "Discover", href: "/", icon: "discover" }] },
  {
    label: "Research",
    items: [
      { label: "My Research", href: "/research", icon: "research" },
      { label: "Reports", href: "/reports", icon: "reports" },
      { label: "Compare", href: "/compare", icon: "compare" },
      { label: "Thesis tracker", href: "/thesis", icon: "thesis" },
      { label: "Change briefs", href: "/briefs", icon: "brief" },
    ],
  },
  { label: "Preferences", items: [{ label: "Settings", href: "/settings", icon: "settings" }] },
];

const adminNavGroup = { label: "Administration", items: [{ label: "Usage & access", href: "/admin", icon: "admin" as const }] };

const coverageItems = [
  { ticker: "NVDA", name: "NVIDIA", href: "/research?company=NVIDIA" },
  { ticker: "HDFCBANK", name: "HDFC Bank", href: "/research?company=HDFC%20Bank" },
  { ticker: "TCS", name: "Tata Consultancy", href: "/research?company=TCS" },
];

function BrandMark() {
  return <span className="global-brand-mark" aria-hidden="true"><i /><i /><i /></span>;
}

function NavIcon({ name }: { name: IconName }) {
  const paths: Record<IconName, React.ReactNode> = {
    discover: <><circle cx="12" cy="12" r="6.5" /><path d="m16.8 16.8 3.7 3.7" /></>,
    research: <><path d="M5 4.5h10.5a3.5 3.5 0 0 1 3.5 3.5v11.5H8.5A3.5 3.5 0 0 0 5 23V4.5Z" /><path d="M8.5 8.5h7M8.5 12h7M8.5 15.5h4" /></>,
    reports: <><path d="M6 3.5h9l4 4V21A2.5 2.5 0 0 1 16.5 23.5h-10A2.5 2.5 0 0 1 4 21V6A2.5 2.5 0 0 1 6.5 3.5Z" /><path d="M15 3.8V8h4.1M8 12h8M8 16h8M8 20h5" /></>,
    compare: <><path d="M7 7h12M15 3l4 4-4 4M17 17H5M9 13l-4 4 4 4" /></>,
    thesis: <><path d="M5 19.5V8.4A2.4 2.4 0 0 1 7.4 6H19v13.5H7.4A2.4 2.4 0 0 0 5 21.9" /><path d="M9 10h6M9 14h5" /><path d="M5 8.5h2" /></>,
    brief: <><path d="M6 3.5h9l4 4V21A2.5 2.5 0 0 1 16.5 23.5h-10A2.5 2.5 0 0 1 4 21V6A2.5 2.5 0 0 1 6.5 3.5Z" /><path d="M15 3.8V8h4.1M8 13h8M8 17h5" /><path d="m16.5 13 1.2 1.2 2.3-2.5" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56v.08h-3v-.08a1.7 1.7 0 0 0-1.03-1.56A1.7 1.7 0 0 0 8.8 19l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7.02 15 1.7 1.7 0 0 0 5.46 14H5.4v-3h.08a1.7 1.7 0 0 0 1.56-1.03A1.7 1.7 0 0 0 6.7 8.1l-.06-.06 2.12-2.12.06.06a1.7 1.7 0 0 0 1.88.34 1.7 1.7 0 0 0 1.03-1.56v-.08h3v.08a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06a1.7 1.7 0 0 0-.34 1.88A1.7 1.7 0 0 0 20.98 11h.08v3h-.08A1.7 1.7 0 0 0 19.4 15Z" /></>,
    admin: <><rect x="4.5" y="4" width="15" height="16" rx="2" /><path d="M8 9h8M8 13h5M8 17h3" /><circle cx="17.5" cy="16.5" r="2" /></>,
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.55" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function isCurrent(pathname: string, href: string) {
  return href === "/" ? pathname === "/" || pathname === "/discover" : pathname.startsWith(href);
}

export function GlobalAppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isLocalPreview, role, signOut } = useDevSession();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Make an old Fast Refresh-preserved compact state recover to the full rail once.
  useEffect(() => {
    setCollapsed(false);
  }, []);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    if (mobileOpen) document.body.style.overflow = "hidden";
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMobileOpen(false);
    }
    if (mobileOpen) document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [mobileOpen]);

  function toggleCollapsed() {
    setCollapsed((current) => !current);
  }

  return (
    <div className={`global-app-shell${collapsed ? " global-app-shell-collapsed" : ""}`}>
      {mobileOpen ? <button className="global-nav-scrim" type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)} /> : null}
      <aside className={`global-sidebar${mobileOpen ? " global-sidebar-open" : ""}`} aria-label="Primary navigation">
        <div className="global-sidebar-inner">
          <div className="global-brand-row">
            <Link className="global-brand" href="/" onClick={() => setMobileOpen(false)}>
              <BrandMark /><span className="global-brand-copy global-nav-label"><strong>Financial Research</strong><small>Evidence intelligence</small></span>
            </Link>
            <button className="global-collapse-button" type="button" onClick={toggleCollapsed} aria-label={collapsed ? "Expand navigation" : "Collapse navigation"} aria-controls="global-primary-nav" aria-expanded={!collapsed} aria-pressed={collapsed}>
              <span aria-hidden="true">{collapsed ? "→" : "←"}</span>
            </button>
          </div>

          <section className="global-coverage" aria-label="Pinned coverage">
            <div className="global-coverage-heading"><span className="global-nav-label">Coverage</span><small className="global-nav-label">Sample</small></div>
            {coverageItems.map((item) => <Link className="global-coverage-item" href={item.href} key={item.ticker} title={collapsed ? `${item.ticker} — ${item.name}` : undefined} onClick={() => setMobileOpen(false)}><strong>{item.ticker}</strong><span className="global-nav-label">{item.name}</span></Link>)}
          </section>

          <nav id="global-primary-nav" className="global-primary-nav">
            {[...navGroups, ...(isLocalPreview && role === "admin" ? [adminNavGroup] : [])].map((group) => (
              <div className="global-nav-group" key={group.label}>
                <p className="global-nav-section">{group.label}</p>
                {group.items.map((item) => {
                  const current = isCurrent(pathname, item.href);
                  return <Link key={item.label} className={`global-nav-item${current ? " global-nav-item-current" : ""}`} href={item.href} data-tooltip={item.label} title={collapsed ? item.label : undefined} aria-current={current ? "page" : undefined} onClick={() => setMobileOpen(false)}>
                    <span className="global-nav-icon" aria-hidden="true"><NavIcon name={item.icon} /></span><span className="global-nav-label">{item.label}</span>
                  </Link>;
                })}
              </div>
            ))}
          </nav>

          <div className="global-sidebar-footer"><span className="global-status-dot" aria-hidden="true" /><span className="global-nav-label">Evidence before explanation.</span></div>
          {isLocalPreview ? <button type="button" className={sessionStyles.session} onClick={signOut} aria-label={`Sign out of local ${role === "admin" ? "administrator" : "researcher"} session`}><strong className="global-nav-label">Local {role === "admin" ? "administrator" : "researcher"}</strong><span className="global-nav-label">Sign out</span></button> : null}
        </div>
      </aside>

      <button className="global-mobile-trigger" type="button" aria-label="Open navigation" aria-controls="global-primary-nav" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><span aria-hidden="true">☰</span></button>
      <div className="global-app-main">{children}</div>
    </div>
  );
}
