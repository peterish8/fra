"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { GoogleIcon } from "@/components/auth/google-icon";
import { mapAuthErrorMessage } from "@/lib/auth/auth-error-message";
import { normalizeLocalPreviewRole, parseLocalPreviewSession, type LocalPreviewRole } from "@/lib/local-preview-session";
import { signInWithGoogle } from "@/lib/auth/oauth-login";
import { getSupabaseBrowserClient, isSupabaseConfigured } from "@/lib/auth/supabase-browser-client";
import styles from "./dev-auth-gate.module.css";

type GoogleStatus = { state: "idle" } | { state: "redirecting" } | { state: "error"; message: string };

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
  const pathname = usePathname();
  const [isDevHost, setIsDevHost] = useState(false);
  const [signedIn, setSignedIn] = useState(true);
  const [role, setRole] = useState<LocalPreviewRole>("researcher");
  const [chosenRole, setChosenRole] = useState<LocalPreviewRole>("researcher");
  const [googleStatus, setGoogleStatus] = useState<GoogleStatus>({ state: "idle" });

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

  // A real Supabase session (e.g. finishing Google sign-in) also counts as
  // signed in here. Without this, the gate never learns about it and keeps
  // reappearing after `/auth/callback` sends the browser to `/research`.
  useEffect(() => {
    if (!isSupabaseConfigured()) return;
    const supabase = getSupabaseBrowserClient();
    let cancelled = false;

    supabase.auth.getSession().then(({ data }) => {
      if (!cancelled && data.session) setSignedIn(true);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) setSignedIn(true);
    });

    return () => {
      cancelled = true;
      listener.subscription.unsubscribe();
    };
  }, []);

  function signIn() {
    window.localStorage.setItem(DEV_AUTH_KEY, JSON.stringify({ role: chosenRole }));
    setRole(chosenRole);
    setSignedIn(true);
  }

  async function handleGoogleSignIn() {
    if (googleStatus.state === "redirecting") return;

    let supabase;
    try {
      supabase = getSupabaseBrowserClient();
    } catch (error) {
      setGoogleStatus({ state: "error", message: mapAuthErrorMessage(error) });
      return;
    }

    setGoogleStatus({ state: "redirecting" });
    const result = await signInWithGoogle(supabase, `${window.location.origin}/auth/callback`);
    if (!result.ok) {
      setGoogleStatus({ state: "error", message: result.message });
    }
    // On success the browser navigates away to Google; nothing else to do here.
  }

  function signOut() {
    if (!isDevHost) return;
    window.localStorage.removeItem(DEV_AUTH_KEY);
    setRole("researcher");
    setChosenRole("researcher");
    setSignedIn(false);
  }

  const session = { isLocalPreview: isDevHost, role: normalizeLocalPreviewRole(role), signOut };
  const isAuthCallbackRoute = pathname?.startsWith("/auth/callback") ?? false;

  if (isDevHost && !signedIn && !isAuthCallbackRoute) {
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

          <div className="auth-divider">or</div>
          <button
            type="button"
            className="auth-button-secondary"
            onClick={handleGoogleSignIn}
            disabled={googleStatus.state === "redirecting"}
            suppressHydrationWarning
          >
            <GoogleIcon />
            {googleStatus.state === "redirecting" ? "Redirecting…" : "Continue with Google"}
          </button>
          {googleStatus.state === "error" ? (
            <p className="auth-error" role="alert">
              {googleStatus.message}
            </p>
          ) : null}

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
