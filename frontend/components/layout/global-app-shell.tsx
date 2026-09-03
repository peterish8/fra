"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

// Versioned so a prior prototype's collapsed preference cannot hide the new rail.
const COLLAPSED_KEY = "financial-research-nav-collapsed-v2";

type NavItem = { label: string; href: string; icon: string };

const navItems: NavItem[] = [
  { label: "Discover", href: "/", icon: "⌕" },
  { label: "My Research", href: "/research", icon: "▤" },
  { label: "Reports", href: "/reports", icon: "▥" },
  { label: "Compare", href: "/compare", icon: "⇄" },
];

function BrandMark() {
  return <span className="global-brand-mark" aria-hidden="true"><i /><i /><i /></span>;
}

function isCurrent(pathname: string, href: string) {
  return href === "/" ? pathname === "/" || pathname === "/discover" : pathname.startsWith(href);
}

export function GlobalAppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setCollapsed(window.localStorage.getItem(COLLAPSED_KEY) === "true");
  }, []);

  useEffect(() => {
    if (!mobileOpen) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMobileOpen(false);
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [mobileOpen]);

  function toggleCollapsed() {
    setCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem(COLLAPSED_KEY, String(next));
      return next;
    });
  }

  return (
    <div className={`global-app-shell${collapsed ? " global-app-shell-collapsed" : ""}`}>
      {mobileOpen ? <button className="global-nav-scrim" type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)} /> : null}
      <aside className={`global-sidebar${mobileOpen ? " global-sidebar-open" : ""}`} aria-label="Primary navigation">
        <div className="global-sidebar-inner">
          <div className="global-brand-row">
            <Link className="global-brand" href="/" onClick={() => setMobileOpen(false)}>
              <BrandMark /><span className="global-nav-label">Financial Research</span>
            </Link>
            <button className="global-collapse-button" type="button" onClick={toggleCollapsed} aria-label={collapsed ? "Expand navigation" : "Collapse navigation"} aria-controls="global-primary-nav" aria-pressed={collapsed}>
              <span aria-hidden="true">{collapsed ? "→" : "←"}</span>
            </button>
          </div>

          <div className="global-welcome">
            <p>Research desk</p>
            <h2>Welcome back.</h2>
            <span>Local demo session · private by default</span>
          </div>

          <nav id="global-primary-nav" className="global-primary-nav">
            <p className="global-nav-section">Workspace</p>
            {navItems.map((item) => (
              <Link key={item.href} className={`global-nav-item${isCurrent(pathname, item.href) ? " global-nav-item-current" : ""}`} href={item.href} aria-current={isCurrent(pathname, item.href) ? "page" : undefined} onClick={() => setMobileOpen(false)}>
                <span className="global-nav-icon" aria-hidden="true">{item.icon}</span><span className="global-nav-label">{item.label}</span>
              </Link>
            ))}
            <p className="global-nav-section global-nav-section-lower">Account</p>
            <Link className="global-nav-item" href="/" onClick={() => setMobileOpen(false)}><span className="global-nav-icon" aria-hidden="true">⚙</span><span className="global-nav-label">Settings</span></Link>
          </nav>

          <div className="global-sidebar-footer"><span className="global-status-dot" aria-hidden="true" /><span className="global-nav-label">Evidence before explanation.</span></div>
        </div>
      </aside>

      <button className="global-mobile-trigger" type="button" aria-label="Open navigation" aria-controls="global-primary-nav" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><span aria-hidden="true">☰</span></button>
      <div className="global-app-main">{children}</div>
    </div>
  );
}
