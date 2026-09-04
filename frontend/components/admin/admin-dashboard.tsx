"use client";

import Link from "next/link";

import { useDevSession } from "@/components/dev/dev-auth-gate";
import { demoAdminUsageOverview, quotaPercentage, type AdminUserUsage } from "@/lib/demo-admin-api";
import styles from "./admin-dashboard.module.css";

function statusClass(status: AdminUserUsage["quota_status"]) {
  if (status === "AT_LIMIT") return styles.statusLimit;
  if (status === "NEARING_LIMIT") return styles.statusWarning;
  return "";
}

function fillClass(status: AdminUserUsage["quota_status"]) {
  if (status === "AT_LIMIT") return styles.fillLimit;
  if (status === "NEARING_LIMIT") return styles.fillWarning;
  return "";
}

function statusLabel(status: AdminUserUsage["quota_status"]) {
  return status === "AT_LIMIT" ? "At limit" : status === "NEARING_LIMIT" ? "Near limit" : "Available";
}

export function AdminDashboard() {
  const { isLocalPreview, role } = useDevSession();
  const overview = demoAdminUsageOverview;

  if (!isLocalPreview || role !== "admin") {
    return <main className={styles.page}><div className={`${styles.frame} ${styles.denied}`}><section className={styles.deniedPanel}><h1>Administrator access required.</h1><p>This workspace exposes usage summaries only to a verified administrator. In local preview, choose the administrator role on the sign-in screen to inspect fixture data.</p><Link className={styles.returnLink} href="/">Return to Discover →</Link></section></div></main>;
  }

  return <main className={styles.page} id="main-content"><div className={styles.frame}>
    <nav className={styles.breadcrumb} aria-label="Breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><strong>Administration</strong></nav>
    <header className={styles.heading}><h1>Usage, <em>with the limits visible.</em></h1><p>Review local account activity and research capacity without exposing provider credentials, tokens, or source data.</p></header>
    <aside className={styles.notice}><span className={styles.noticeMark} aria-hidden="true">i</span><span><strong>Local fixture data.</strong> These counts are a localhost preview. Production usage must come from durable server-side quota and audit records.</span></aside>
    <section className={styles.metrics} aria-label="Usage summary">
      <article className={styles.metric}><span>Registered accounts</span><strong>{overview.registered_users}</strong><small>Local fixture identities</small></article>
      <article className={styles.metric}><span>Active in the last {overview.observation_window_hours} hours</span><strong>{overview.active_users_in_window}</strong><small>Accounts with research activity</small></article>
      <article className={styles.metric}><span>Research runs in the last {overview.observation_window_hours} hours</span><strong>{overview.research_runs_in_window}</strong><small>Across all preview accounts</small></article>
    </section>
    <section aria-labelledby="quota-heading"><div className={styles.sectionHeader}><div><h2 id="quota-heading">Per-user research limits</h2><p>Window: rolling {overview.observation_window_hours} hours · refreshed from the configured admin source.</p></div><p>{overview.data_mode === "FIXTURE" ? "Preview mode" : "Live mode"}</p></div>
      <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th scope="col">Account</th><th scope="col">Role</th><th scope="col">Research allowance</th><th scope="col">State</th></tr></thead><tbody>{overview.users.map((user) => { const percentage = quotaPercentage(user); return <tr key={user.user_id}><td><div className={styles.person}><strong>{user.display_name}</strong><span>{user.user_id}</span></div></td><td><span className={styles.role}>{user.role === "ADMIN" ? "Administrator" : "Researcher"}</span></td><td><div className={styles.usage}><div className={styles.usageLine}><span>{user.research_runs_used} used</span><span>{user.research_runs_limit} total</span></div><div className={styles.track} aria-label={`${user.research_runs_used} of ${user.research_runs_limit} research runs used`}><div className={`${styles.fill} ${fillClass(user.quota_status)}`} style={{ width: `${percentage}%` }} /></div></div></td><td><span className={`${styles.status} ${statusClass(user.quota_status)}`}>{statusLabel(user.quota_status)}</span></td></tr>; })}</tbody></table></div>
    </section>
    <section className={styles.access} aria-label="Access safeguards"><article className={styles.accessCard}><h3>Role source</h3><p>The local role picker is only a preview control. A deployed administrator must be established by a verified identity claim at the backend.</p></article><article className={styles.accessCard}><h3>Operational boundary</h3><p>This view is read-only. It deliberately omits API keys, access tokens, provider configuration, and unredacted research content.</p></article></section>
  </div></main>;
}
