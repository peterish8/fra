export default function Loading() {
  return (
    <main className="main-content route-loading" aria-busy="true" aria-live="polite">
      <div className="route-loading-inner">
        <span className="route-loading-kicker">Financial Research</span>
        <div className="route-loading-line route-loading-line-wide" />
        <div className="route-loading-line route-loading-line-short" />
        <div className="route-loading-panel"><span /><span /><span /></div>
      </div>
    </main>
  );
}
