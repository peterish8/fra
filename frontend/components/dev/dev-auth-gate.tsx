"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { normalizeLocalPreviewRole, parseLocalPreviewSession, type LocalPreviewRole } from "@/lib/local-preview-session";
import styles from "./dev-auth-gate.module.css";

const DEV_AUTH_KEY = "financial-research-dev-auth";

type DevSession = {
  isLocalPreview: boolean;
  role: LocalPreviewRole;
  signOut: () => void;
};

const DevSessionContext = createContext<DevSession>({
  isLocalPreview: false,
  role: "researcher",
  signOut: () => undefined,
});

function isLocalhost() {
  return window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
}

export function DevAuthGate({ children }: { children: React.ReactNode }) {
  // Render the app shell immediately on the server. A blocking loader here
  // would leave the whole workspace blank if a development HMR/client bundle
  // fails before hydration. The localhost-only gate is applied after mount.
  const [isDevHost, setIsDevHost] = useState(false);
  const [signedIn, setSignedIn] = useState(true);
  const [role, setRole] = useState<LocalPreviewRole>("researcher");
  const [chosenRole, setChosenRole] = useState<LocalPreviewRole>("researcher");

  useEffect(() => {
    const local = isLocalhost();
    setIsDevHost(local);
    const storedSession = parseLocalPreviewSession(window.localStorage.getItem(DEV_AUTH_KEY));
    setSignedIn(!local || storedSession !== null);
    if (storedSession) {
      setRole(storedSession.role);
      setChosenRole(storedSession.role);
    }
  }, []);

  function signIn() {
    window.localStorage.setItem(DEV_AUTH_KEY, JSON.stringify({ role: chosenRole }));
    setRole(chosenRole);
    setSignedIn(true);
  }

  function signOut() {
    if (!isDevHost) return;
    window.localStorage.removeItem(DEV_AUTH_KEY);
    setRole("researcher");
    setChosenRole("researcher");
    setSignedIn(false);
  }

  const session = { isLocalPreview: isDevHost, role: normalizeLocalPreviewRole(role), signOut };

  if (isDevHost && !signedIn) {
    return (
      <main className="dev-auth-screen">
        <div className="dev-auth-card">
          <div className="dev-auth-mark" aria-hidden="true"><span /><span /><span /></div>
          <p className="dev-auth-kicker">Local development mode</p>
          <h1>Welcome back to your research desk.</h1>
          <p>Choose a local preview role to explore the product with safe fixture data. No account or provider keys are used in this mode.</p>
          <div className={styles.roleChooser} role="radiogroup" aria-label="Local preview role">
            <button type="button" role="radio" aria-checked={chosenRole === "researcher"} className={`${styles.roleOption}${chosenRole === "researcher" ? ` ${styles.roleOptionSelected}` : ""}`} onClick={() => setChosenRole("researcher")}>
              <span className={styles.roleIndicator} aria-hidden="true">{chosenRole === "researcher" ? "✓" : ""}</span><span><strong>Researcher</strong><small>Research workspaces, reports, comparisons, and personal settings.</small></span>
            </button>
            <button type="button" role="radio" aria-checked={chosenRole === "admin"} className={`${styles.roleOption}${chosenRole === "admin" ? ` ${styles.roleOptionSelected}` : ""}`} onClick={() => setChosenRole("admin")}>
              <span className={styles.roleIndicator} aria-hidden="true">{chosenRole === "admin" ? "✓" : ""}</span><span><strong>Administrator</strong><small>Includes the local usage and quota overview for product review.</small></span>
            </button>
          </div>
          <p className={styles.roleNotice}>This selector exists only on localhost. It does not grant a production role; deployed admin access must come from a verified server-side claim.</p>
          <button type="button" className="dev-auth-button" onClick={signIn}>Continue as {chosenRole === "admin" ? "local administrator" : "demo researcher"} <span aria-hidden="true">→</span></button>
          <small>Only enabled on localhost. Production authentication remains protected.</small>
        </div>
      </main>
    );
  }

  return <DevSessionContext.Provider value={session}>{children}</DevSessionContext.Provider>;
}

export function useDevSession() {
  return useContext(DevSessionContext);
}
