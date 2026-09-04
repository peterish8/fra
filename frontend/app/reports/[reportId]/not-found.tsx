import Link from "next/link";

export default function ReportNotFound() {
  return (
    <main className="main-content route-error">
      <div className="route-error-card">
        <span className="route-loading-kicker">404 · Missing report</span>
        <h1>This report isn’t available.</h1>
        <p>The report id may be wrong, or the workspace was removed from the local preview library.</p>
        <div>
          <Link className="route-primary-button" href="/reports">
            Back to Reports
          </Link>
          <Link className="route-secondary-link" href="/research">
            Open My Research
          </Link>
        </div>
      </div>
    </main>
  );
}
