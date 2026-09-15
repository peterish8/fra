import { Suspense } from "react";

import { OAuthCallback } from "@/components/auth/oauth-callback";

function CallbackFallback() {
  return (
    <main className="main-content route-loading" aria-busy="true" aria-live="polite">
      <div className="route-loading-inner">
        <span className="route-loading-trace" aria-hidden="true"><i /><i /><i /></span>
        <p className="route-loading-kicker">Finishing sign-in</p>
        <h1>Bringing the research desk into focus.</h1>
      </div>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<CallbackFallback />}>
      <OAuthCallback />
    </Suspense>
  );
}
