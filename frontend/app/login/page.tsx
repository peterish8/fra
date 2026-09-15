import { Suspense } from "react";

import { LoginForm } from "@/components/auth/login-form";

function LoginFallback() {
  return (
    <main className="main-content route-loading" aria-busy="true" aria-live="polite">
      <div className="route-loading-inner">
        <span className="route-loading-trace" aria-hidden="true"><i /><i /><i /></span>
        <p className="route-loading-kicker">Opening sign-in</p>
        <h1>Bringing the research desk into focus.</h1>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginForm />
    </Suspense>
  );
}
