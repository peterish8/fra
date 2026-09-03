"use client";

import { useEffect, useState } from "react";

const DEV_AUTH_KEY = "financial-research-dev-auth";

function isLocalhost() {
  return window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
}

export function DevAuthGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    if (!isLocalhost()) {
      setReady(true);
      return;
    }
    setSignedIn(window.localStorage.getItem(DEV_AUTH_KEY) === "true");
    setReady(true);
  }, []);

  function signIn() {
    window.localStorage.setItem(DEV_AUTH_KEY, "true");
    setSignedIn(true);
  }

  if (!ready) {
    return <div className="dev-auth-loading" role="status">Preparing your workspace…</div>;
  }

  if (isLocalhost() && !signedIn) {
    return (
      <main className="dev-auth-screen">
        <div className="dev-auth-card">
          <div className="dev-auth-mark" aria-hidden="true"><span /><span /><span /></div>
          <p className="dev-auth-kicker">Local development mode</p>
          <h1>Welcome back to your research desk.</h1>
          <p>Use the one-click developer session to explore the full product with safe fixture data. No account or provider keys are used in this mode.</p>
          <button type="button" className="dev-auth-button" onClick={signIn}>Continue as demo researcher <span aria-hidden="true">→</span></button>
          <small>Only enabled on localhost. Production authentication remains protected.</small>
        </div>
      </main>
    );
  }

  return <>{children}</>;
}

