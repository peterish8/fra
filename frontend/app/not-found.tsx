import Link from "next/link";

export default function NotFound() {
  return <main className="main-content route-error"><div className="route-error-card"><span className="route-loading-kicker">404 · Missing view</span><h1>This research view isn’t here.</h1><p>The workspace may have moved, or the requested report is no longer available.</p><Link className="route-primary-button" href="/">Return to Discover</Link></div></main>;
}
