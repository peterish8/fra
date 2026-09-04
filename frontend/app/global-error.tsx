"use client";

import Link from "next/link";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <main className="main-content route-error" role="alert">
          <div className="route-error-card">
            <span className="route-loading-kicker">Workspace interruption</span>
            <h1>We couldn’t recover this view.</h1>
            <p>The research desk hit an unexpected error. Try again, or return to Discover while the workspace resets.</p>
            <div>
              <button type="button" className="route-primary-button" onClick={() => reset()}>
                Try again
              </button>
              <Link href="/" className="route-secondary-link">
                Back to Discover
              </Link>
            </div>
          </div>
        </main>
      </body>
    </html>
  );
}
