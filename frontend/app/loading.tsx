export default function Loading() {
  return (
    <main className="main-content route-loading" aria-busy="true" aria-live="polite">
      <div className="route-loading-inner">
        <span className="route-loading-trace" aria-hidden="true"><i /><i /><i /></span>
        <p className="route-loading-kicker">Opening workspace</p>
        <h1>Bringing the research desk into focus.</h1>
        <p className="route-loading-copy">Restoring the workspace and its evidence context.</p>
        <div className="route-loading-status" role="status">
          <span aria-hidden="true" />
          Preparing the record
        </div>
      </div>
    </main>
  );
}
