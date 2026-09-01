"use client";

import { useState } from "react";

import styles from "./research-workspace.module.css";
import {
  formatReportDate,
  STATUS_OPTIONS,
  statusLabel,
  type ReportStatus,
  type ReportSummary,
} from "./research-types";

type ResearchLibraryProps = {
  error: string | null;
  filterStatus: string;
  isLoading: boolean;
  items: ReportSummary[];
  query: string;
  deletingId: string | null;
  onDelete: (report: ReportSummary) => Promise<void>;
  onOpen: (report: ReportSummary) => Promise<void>;
  onQueryChange: (value: string) => void;
  onRetry: () => void;
  onStatusChange: (value: string) => void;
};

function StatusBadge({ status }: { status: ReportStatus }) {
  const icon = status === "VERIFIED" || status === "READY" ? "✓" : status === "RESEARCHING" ? "◌" : "○";
  return (
    <span className={`${styles.statusBadge} ${styles[`status${status}`] ?? ""}`}>
      <span aria-hidden="true">{icon}</span>
      <span>{statusLabel(status)}</span>
    </span>
  );
}

function LibraryLoading() {
  return (
    <div className={styles.loadingState} role="status" aria-live="polite">
      <span className={styles.loadingMark} aria-hidden="true">◌</span>
      <div>
        <strong>Loading your research library</strong>
        <p>Fetching only workspaces available to your authenticated account.</p>
      </div>
    </div>
  );
}

export function ResearchLibrary({
  error,
  filterStatus,
  isLoading,
  items,
  query,
  deletingId,
  onDelete,
  onOpen,
  onQueryChange,
  onRetry,
  onStatusChange,
}: ResearchLibraryProps) {
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  return (
    <section className={styles.librarySection} aria-labelledby="library-title">
      <div className={styles.sectionHeader}>
        <div>
          <p className={styles.eyebrow}>Your workspaces</p>
          <h2 id="library-title">Research library</h2>
        </div>
        <span className={styles.itemCount} aria-label={`${items.length} visible workspaces`}>{items.length}</span>
      </div>

      <div className={styles.libraryControls}>
        <label className={styles.searchBox}>
          <span className={styles.searchIcon} aria-hidden="true">⌕</span>
          <span className={styles.srOnly}>Search your research workspaces</span>
          <input
            type="search"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search workspaces"
          />
        </label>
        <label className={styles.filterBox}>
          <span className={styles.srOnly}>Filter workspaces by status</span>
          <select value={filterStatus} onChange={(event) => onStatusChange(event.target.value)}>
            {STATUS_OPTIONS.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
          </select>
        </label>
      </div>

      {error ? (
        <div className={styles.errorState} role="alert">
          <span className={styles.alertIcon} aria-hidden="true">!</span>
          <div>
            <strong>Research library unavailable</strong>
            <p>{error}</p>
            <button className={styles.secondaryButton} type="button" onClick={onRetry}>Try again</button>
          </div>
        </div>
      ) : isLoading ? <LibraryLoading /> : items.length === 0 ? (
        <div className={styles.emptyLibrary}>
          <span className={styles.emptyIcon} aria-hidden="true">⌁</span>
          <div>
            <h3>{query || filterStatus ? "No matching workspaces" : "Your library is ready"}</h3>
            <p>{query || filterStatus ? "Try a different search or status filter. Nothing has been inferred or added." : "Create a workspace above to keep company research persistent and inspectable."}</p>
          </div>
        </div>
      ) : (
        <ul className={styles.libraryList}>
          {items.map((report) => {
            const isConfirming = confirmingId === report.report_id;
            const isDeleting = deletingId === report.report_id;
            return (
              <li className={styles.libraryItem} key={report.report_id}>
                <button className={styles.reportOpenButton} type="button" onClick={() => void onOpen(report)} disabled={isDeleting}>
                  <span className={styles.reportGlyph} aria-hidden="true">▤</span>
                  <span className={styles.reportCopy}>
                    <strong>{report.title}</strong>
                    <span><StatusBadge status={report.status} /> <span className={styles.updatedAt}>Updated {formatReportDate(report.updated_at)}</span></span>
                  </span>
                  <span className={styles.chevron} aria-hidden="true">→</span>
                </button>
                {isConfirming ? (
                  <div className={styles.deleteConfirm} role="group" aria-label={`Delete ${report.title}`}>
                    <span>Delete this workspace?</span>
                    <button type="button" className={styles.cancelButton} onClick={() => setConfirmingId(null)} disabled={isDeleting}>Cancel</button>
                    <button type="button" className={styles.deleteButton} onClick={() => void onDelete(report)} disabled={isDeleting}>{isDeleting ? "Deleting…" : "Delete"}</button>
                  </div>
                ) : (
                  <button className={styles.deleteTrigger} type="button" onClick={() => setConfirmingId(report.report_id)} aria-label={`Delete ${report.title}`} disabled={isDeleting}>
                    <span aria-hidden="true">×</span>
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
