"use client";

import { useState } from "react";

import { GoogleIcon } from "@/components/auth/google-icon";
import { mapAuthErrorMessage } from "@/lib/auth/auth-error-message";
import { signInWithGoogle } from "@/lib/auth/oauth-login";
import { getSupabaseBrowserClient } from "@/lib/auth/supabase-browser-client";

type Status = { state: "idle" } | { state: "redirecting" } | { state: "error"; message: string };

/** A real, working Google sign-in entry point in the shared sidebar (every route, including Discover). */
export function SidebarGoogleSignIn() {
  const [status, setStatus] = useState<Status>({ state: "idle" });
  const isBusy = status.state === "redirecting";

  async function handleClick() {
    if (isBusy) return;

    let supabase;
    try {
      supabase = getSupabaseBrowserClient();
    } catch (error) {
      setStatus({ state: "error", message: mapAuthErrorMessage(error) });
      return;
    }

    setStatus({ state: "redirecting" });
    const result = await signInWithGoogle(supabase, `${window.location.origin}/auth/callback`);
    if (!result.ok) {
      setStatus({ state: "error", message: result.message });
    }
    // On success the browser navigates away to Google; nothing else to do here.
  }

  return (
    <div className="global-sidebar-google">
      <button
        type="button"
        className="global-sidebar-google-button"
        onClick={handleClick}
        disabled={isBusy}
        title="Continue with Google"
        suppressHydrationWarning
      >
        <GoogleIcon />
        <span className="global-nav-label">{isBusy ? "Redirecting…" : "Continue with Google"}</span>
      </button>
      {status.state === "error" ? (
        <p className="global-sidebar-google-error global-nav-label" role="alert">
          {status.message}
        </p>
      ) : null}
    </div>
  );
}
