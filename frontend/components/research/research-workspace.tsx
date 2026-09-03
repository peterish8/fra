"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { ResearchForm } from "./research-form";
import { ResearchLibrary } from "./research-library";
import styles from "./research-workspace.module.css";
import {
  errorMessage,
  statusLabel,
  type CreateReportRequest,
  type ReportApiClient,
  type ReportDetail,
  type ReportListResponse,
  type ReportSummary,
} from "./research-types";

type ResearchWorkspaceProps = {
  apiClient?: ReportApiClient;
};

function createIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `research-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function DetailPanel({ report, isLoading, error, onClose }: { report: ReportSummary | null; isLoading: boolean; error: string | null; onClose: () => void }) {
  if (!report && !isLoading && !error) return null;
  return (
    <section className={styles.detailPanel} aria-labelledby="workspace-detail-title">
      <div className={styles.detailHeader}>
        <div>
          <p className={styles.eyebrow}>Workspace</p>
          <h2 id="workspace-detail-title">{report?.title ?? "Opening workspace"}</h2>
        </div>
        <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Close workspace details">×</button>
      </div>
      {isLoading ? (
        <div className={styles.loadingState} role="status"><span className={styles.loadingMark} aria-hidden="true">◌</span><span>Opening the saved workspace…</span></div>
      ) : error ? (
        <div className={styles.errorState} role="alert"><span className={styles.alertIcon} aria-hidden="true">!</span><p>{error}</p></div>
      ) : report ? (
        <>
          <div className={styles.detailMeta}>
            <div><span>Status</span><strong><span aria-hidden="true">○</span> {statusLabel(report.status)}</strong></div>
            <div><span>Current version</span><strong>{report.current_version === null ? "Not created yet" : `v${report.current_version}`}</strong></div>
            <div><span>Last updated</span><strong>{new Date(report.updated_at).toLocaleString()}</strong></div>
          </div>
          <div className={styles.detailNotice}>
            <span aria-hidden="true">i</span>
            <p>This workspace contains research metadata only so far. No claims, evidence, or company identity has been invented in this view.</p>
          </div>
        </>
      ) : null}
    </section>
  );
}

export function ResearchWorkspace({ apiClient }: ResearchWorkspaceProps) {
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isNavCollapsed, setIsNavCollapsed] = useState(false);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(Boolean(apiClient));
  const [libraryError, setLibraryError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<ReportSummary | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    if (!apiClient) {
      setIsLoading(false);
      setLibraryError("Your authenticated API client is not connected. Pass one into this workspace to load private reports.");
      return;
    }
    setIsLoading(true);
    setLibraryError(null);
    try {
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      if (status) params.set("status", status);
      const suffix = params.toString();
      const page = await apiClient.get<ReportListResponse>(`/v1/reports${suffix ? `?${suffix}` : ""}`);
      setReports(page.items);
    } catch (error: unknown) {
      setLibraryError(errorMessage(error, "We could not load your research workspaces."));
    } finally {
      setIsLoading(false);
    }
  }, [apiClient, query, status]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadReports(), query ? 220 : 0);
    return () => window.clearTimeout(timer);
  }, [loadReports, query]);

  async function createReport(request: CreateReportRequest) {
    if (!apiClient) {
      setFormError("Your authenticated API client is not connected. The workspace was not created.");
      return;
    }
    setIsCreating(true);
    setFormError(null);
    setFeedback(null);
    try {
      const created = await apiClient.post<ReportSummary>("/v1/reports", request, {
        headers: { "Idempotency-Key": createIdempotencyKey() },
      });
      setReports((current) => [created, ...current.filter((report) => report.report_id !== created.report_id)]);
      setSelectedReport(created);
      setFeedback("Workspace created with DRAFT status. Entity resolution and research have not been claimed yet.");
    } catch (error: unknown) {
      setFormError(errorMessage(error, "We could not create this workspace. Check the fields and try again."));
      throw error;
    } finally {
      setIsCreating(false);
    }
  }

  async function openReport(report: ReportSummary) {
    if (!apiClient) return;
    setSelectedReport(report);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const detail = await apiClient.get<ReportDetail>(`/v1/reports/${encodeURIComponent(report.report_id)}`);
      setSelectedReport(detail);
    } catch (error: unknown) {
      setDetailError(errorMessage(error, "We could not open this workspace."));
    } finally {
      setDetailLoading(false);
    }
  }

  async function deleteReport(report: ReportSummary) {
    if (!apiClient) return;
    setDeletingId(report.report_id);
    setLibraryError(null);
    try {
      await apiClient.delete<void>(`/v1/reports/${encodeURIComponent(report.report_id)}`);
      setReports((current) => current.filter((item) => item.report_id !== report.report_id));
      if (selectedReport?.report_id === report.report_id) setSelectedReport(null);
      setFeedback(`“${report.title}” was removed from your library. Shared evidence is preserved.`);
    } catch (error: unknown) {
      setLibraryError(errorMessage(error, "We could not remove this workspace. Nothing was changed."));
    } finally {
      setDeletingId(null);
    }
  }

  const librarySummary = useMemo(() => {
    if (!apiClient) return "Authenticated connection required";
    if (isLoading) return "Syncing your private library";
    return `${reports.length} ${reports.length === 1 ? "workspace" : "workspaces"} visible`;
  }, [apiClient, isLoading, reports.length]);

  return (
    <div className={`${styles.pageShell} ${isNavCollapsed ? styles.navCollapsed : ""}`}>
      <a className={styles.skipLink} href="#research-main">Skip to research workspace</a>
      {isNavOpen ? <button className={styles.navScrim} type="button" aria-label="Close navigation" onClick={() => setIsNavOpen(false)} /> : null}
      <aside className={`${styles.sidebar} ${isNavOpen ? styles.sidebarOpen : ""}`} aria-label="Research navigation">
        <Link href="/" className={styles.brand} onClick={() => setIsNavOpen(false)}><span className={styles.brandMark} aria-hidden="true"><i /><i /><i /></span><span className={styles.navLabel}>Financial Research</span></Link>
        <nav aria-label="Primary navigation" className={styles.primaryNav}>
          <Link href="/" className={styles.navItem} onClick={() => setIsNavOpen(false)}><span aria-hidden="true">⌕</span><span className={styles.navLabel}>Discover</span></Link>
          <Link href="/research" className={`${styles.navItem} ${styles.navItemCurrent}`} aria-current="page" onClick={() => setIsNavOpen(false)}><span aria-hidden="true">▤</span><span className={styles.navLabel}>My Research</span></Link>
          <Link href="/compare" className={styles.navItem} onClick={() => setIsNavOpen(false)}><span aria-hidden="true">⇄</span><span className={styles.navLabel}>Compare</span></Link>
          <Link href="/" className={styles.navItem} onClick={() => setIsNavOpen(false)}><span aria-hidden="true">⚙</span><span className={styles.navLabel}>Settings</span></Link>
        </nav>
        <div className={styles.sidebarLibrary}>
          <div className={styles.sidebarHeading}><span>Recent research</span><span>{reports.length}</span></div>
          {reports.length ? reports.slice(0, 4).map((report) => <button type="button" key={report.report_id} onClick={() => void openReport(report)}>{report.title}<small>{statusLabel(report.status)}</small></button>) : <p>Your saved workspaces will appear here.</p>}
        </div>
        <p className={styles.sidebarFootnote}>Evidence before explanation.</p>
      </aside>

      <main className={styles.mainContent} id="research-main">
        <header className={styles.topBar}>
          <button className={styles.navToggle} type="button" onClick={() => { setIsNavOpen(true); setIsNavCollapsed((current) => !current); }} aria-label={isNavCollapsed ? "Expand navigation" : "Collapse navigation"} aria-expanded={isNavOpen}>
            <span aria-hidden="true">{isNavCollapsed ? "→" : "←"}</span><span className={styles.navToggleLabel}>{isNavCollapsed ? "Open rail" : "Collapse"}</span>
          </button>
          <div><span>Workspace</span><span aria-hidden="true">/</span><strong>My Research</strong></div><span className={styles.connectionStatus}><span aria-hidden="true">{apiClient ? "●" : "○"}</span>{librarySummary}</span>
        </header>
        <div className={styles.contentFrame}>
          <section className={styles.hero} aria-labelledby="research-page-title">
            <div><p className={styles.eyebrow}>Phase 02 · Workspace and entity resolution</p><h1 id="research-page-title">Research that stays inspectable.</h1><p>Build a persistent company workspace before the evidence work begins. Start with identifiers, choose your focus, and keep uncertainty visible.</p></div>
            <div className={styles.heroAside}><span aria-hidden="true">01</span><p>Workspace first<br /><strong>Evidence next</strong></p><small>Private by default</small></div>
          </section>

          <div className={styles.signalStrip} aria-label="Research workflow">
            <div className={styles.signalItem}><span>01</span><strong>Subject</strong><small>Who is being researched</small></div>
            <div className={styles.signalRule} aria-hidden="true" />
            <div className={styles.signalItem}><span>02</span><strong>Evidence</strong><small>What can be supported</small></div>
            <div className={styles.signalRule} aria-hidden="true" />
            <div className={styles.signalItem}><span>03</span><strong>Report</strong><small>What remains uncertain</small></div>
          </div>

          <ResearchForm disabled={isCreating} error={formError} onSubmit={createReport} />
          {feedback ? <div className={styles.successNotice} role="status"><span aria-hidden="true">✓</span><span>{feedback}</span><button type="button" onClick={() => setFeedback(null)} aria-label="Dismiss notification">×</button></div> : null}

          <ResearchLibrary
            error={libraryError}
            filterStatus={status}
            isLoading={isLoading}
            items={reports}
            query={query}
            deletingId={deletingId}
            onDelete={deleteReport}
            onOpen={openReport}
            onQueryChange={setQuery}
            onRetry={() => void loadReports()}
            onStatusChange={setStatus}
          />
          <DetailPanel report={selectedReport} isLoading={detailLoading} error={detailError} onClose={() => { setSelectedReport(null); setDetailError(null); }} />
          <footer className={styles.pageFooter}><span>Research discovery, not investment advice.</span><span>Private workspaces are owner-scoped by the authenticated API.</span></footer>
        </div>
      </main>
    </div>
  );
}

export default ResearchWorkspace;
