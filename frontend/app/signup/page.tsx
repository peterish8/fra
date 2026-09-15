import { Suspense } from "react";

import { SignupForm } from "@/components/auth/signup-form";

function SignupFallback() {
  return (
    <main className="main-content route-loading" aria-busy="true" aria-live="polite">
      <div className="route-loading-inner">
        <span className="route-loading-trace" aria-hidden="true"><i /><i /><i /></span>
        <p className="route-loading-kicker">Opening sign-up</p>
        <h1>Bringing the research desk into focus.</h1>
      </div>
    </main>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<SignupFallback />}>
      <SignupForm />
    </Suspense>
  );
}
