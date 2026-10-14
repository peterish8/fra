"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useDevSession } from "@/components/dev/dev-auth-gate";
import { SidebarGoogleSignIn } from "./sidebar-google-signin";
import styles from "./pill-nav.module.css";
import sessionStyles from "./local-session.module.css";

type NavItem = { label: string; href: string };

const navGroups: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "Workspace",
    items: [
      { label: "Discover", href: "/" },
      { label: "Daily News", href: "/news" },
    ],
  },
  {
    label: "Research",
    items: [
      { label: "My Research", href: "/research" },
      { label: "Reports", href: "/reports" },
      { label: "Compare", href: "/compare" },
      { label: "Thesis tracker", href: "/thesis" },
      { label: "Change briefs", href: "/briefs" },
    ],
  },
  { label: "Preferences", items: [{ label: "Settings", href: "/settings" }] },
];

const adminNavGroup = { label: "Administration", items: [{ label: "Usage & access", href: "/admin" }] };

function BrandMark() {
  return <span className="global-brand-mark" aria-hidden="true"><i /><i /><i /></span>;
}

function isCurrent(pathname: string, href: string) {
  return href === "/" ? pathname === "/" || pathname === "/discover" : pathname.startsWith(href);
}

export function GlobalAppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isLocalPreview, role, signOut } = useDevSession();
  const groups = [...navGroups, ...(isLocalPreview && role === "admin" ? [adminNavGroup] : [])];

  return (
    <div className="global-app-shell">
      <header className={styles.header}>
        <Link className={`global-brand ${styles.brand}`} href="/" aria-label="Financial Research home">
          <BrandMark /><span className={styles.brandName}>Financial Research</span>
        </Link>

        <nav className={styles.pill} aria-label="Primary navigation">
          {groups.map((group, index) => (
            <div className={styles.group} role="group" aria-label={group.label} key={group.label}>
              {index > 0 ? <span className={styles.divider} aria-hidden="true" /> : null}
              {group.items.map((item) => {
                const current = isCurrent(pathname, item.href);
                return <Link key={item.label} className={`${styles.item}${current ? ` ${styles.current}` : ""}`} href={item.href} aria-current={current ? "page" : undefined}>{item.label}</Link>;
              })}
            </div>
          ))}
        </nav>

        <div className={styles.actions}>
          <SidebarGoogleSignIn />
          {isLocalPreview ? <button type="button" className={sessionStyles.session} onClick={signOut} aria-label={`Sign out of local ${role === "admin" ? "administrator" : "researcher"} session`}><strong>{role === "admin" ? "Admin" : "Researcher"}</strong><span>Sign out</span></button> : null}
        </div>
      </header>
      <div className={styles.main}>{children}</div>
    </div>
  );
}
