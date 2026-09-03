"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type NavItem = { label: string; href: string; icon: string };

const navGroups: Array<{ label: string; items: NavItem[] }> = [
  { label: "Overview", items: [{ label: "Discover", href: "/", icon: "⌕" }] },
  {
    label: "Research",
    items: [
      { label: "My Research", href: "/research", icon: "▤" },
      { label: "Reports", href: "/reports", icon: "▥" },
      { label: "Compare", href: "/compare", icon: "⇄" },
    ],
  },
  { label: "Account", items: [{ label: "Settings", href: "/", icon: "⚙" }] },
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

          <div className="global-welcome">
            <p>Research desk</p>
            <h2>Welcome<br />back.</h2>
            <span>Local session · private by default</span>
          </div>

          <nav id="global-primary-nav" className="global-primary-nav">
            {navGroups.map((group) => (
              <div className="global-nav-group" key={group.label}>
                <p className="global-nav-section">{group.label}</p>
                {group.items.map((item) => {
                  const current = isCurrent(pathname, item.href) && item.label !== "Settings";
                  return <Link key={item.label} className={`global-nav-item${current ? " global-nav-item-current" : ""}`} href={item.href} title={collapsed ? item.label : undefined} aria-current={current ? "page" : undefined} onClick={() => setMobileOpen(false)}>
                    <span className="global-nav-icon" aria-hidden="true">{item.icon}</span><span className="global-nav-label">{item.label}</span>
                  </Link>;
                })}
              </div>
            ))}
          </nav>

          <div className="global-sidebar-footer"><span className="global-status-dot" aria-hidden="true" /><span className="global-nav-label">Evidence before explanation.</span></div>
        </div>
      </aside>

      <button className="global-mobile-trigger" type="button" aria-label="Open navigation" aria-controls="global-primary-nav" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><span aria-hidden="true">☰</span></button>
      <div className="global-app-main">{children}</div>
    </div>
  );
}
