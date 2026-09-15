"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { mapAuthErrorMessage } from "@/lib/auth/auth-error-message";
import { extractOAuthErrorFromUrl } from "@/lib/auth/oauth-login";
import { getSupabaseBrowserClient } from "@/lib/auth/supabase-browser-client";

export function OAuthCallback() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function finishSignIn() {
      const urlError = extractOAuthErrorFromUrl(window.location.search, window.location.hash);
      if (urlError) {
        if (!cancelled) setError(urlError);
        return;
      }

      try {
        const supabase = getSupabaseBrowserClient();
        const { data, error: sessionError } = await supabase.auth.getSession();
        if (cancelled) return;
        if (sessionError || !data.session) {
          setError(
            sessionError
              ? mapAuthErrorMessage(sessionError)
              : "We couldn't complete Google sign-in. Try again.",
          );
          return;
        }
        router.replace("/research");
      } catch (thrown) {
        if (!cancelled) setError(mapAuthErrorMessage(thrown));
      }
    }

    finishSignIn();
    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <main className="auth-screen">
      <div className="auth-card">
        <div className="dev-auth-mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <p className="auth-kicker">Sign in</p>
        <h1>{error ? "Sign-in didn't complete." : "Finishing sign-in…"}</h1>

        {error ? (
          <>
            <p className="auth-error" role="alert">
              {error}
            </p>
            <Link href="/login" className="auth-button">
              Back to sign in <span aria-hidden="true">→</span>
            </Link>
          </>
        ) : (
          <p className="auth-subtitle">Connecting your Google account…</p>
        )}
      </div>
    </main>
  );
}
