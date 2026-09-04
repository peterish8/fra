import { Suspense } from "react";

import { DemoResearchPage } from "@/components/research/demo-research-page";

function ResearchFallback() {
  return (
    <main className="main-content route-loading" aria-busy="true" aria-live="polite">
      <div className="route-loading-inner">
        <span className="route-loading-trace" aria-hidden="true"><i /><i /><i /></span>
        <p className="route-loading-kicker">Opening workspace</p>
        <h1>Bringing the research desk into focus.</h1>
        <p className="route-loading-copy">Restoring your research library and create form.</p>
      </div>
    </main>
  );
}

export default function ResearchPage() {
  return (
    <Suspense fallback={<ResearchFallback />}>
      <DemoResearchPage />
    </Suspense>
  );
}
