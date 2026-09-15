import { mapAuthErrorMessage } from "./auth-error-message";

type OAuthError = { message: string; code?: string } | null;

/** The slice of a Supabase client `signInWithGoogle` needs — kept minimal so tests can mock it. */
type OAuthOnly = {
  auth: {
    signInWithOAuth: (credentials: {
      provider: "google";
      options?: { redirectTo?: string };
    }) => Promise<{ error: OAuthError }>;
  };
};

export type OAuthActionResult = { ok: true } | { ok: false; message: string };

/**
 * Start the Google OAuth redirect. On success the browser navigates away to
 * Google immediately; this only ever resolves with `{ ok: false }` if the
 * request could not even be started (e.g. the provider isn't configured).
 */
export async function signInWithGoogle(
  supabase: OAuthOnly,
  redirectTo: string,
): Promise<OAuthActionResult> {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo },
  });
  if (error) return { ok: false, message: mapAuthErrorMessage(error) };
  return { ok: true };
}

/**
 * Supabase reports a failed/cancelled OAuth attempt by appending `error` /
 * `error_description` to either the callback URL's query string (PKCE-style)
 * or its hash fragment (implicit-style). Pure and DOM-free so it's testable
 * without a browser: pass `window.location.search` and `window.location.hash`.
 */
export function extractOAuthErrorFromUrl(search: string, hash: string): string | null {
  const queryParams = new URLSearchParams(search);
  const hashParams = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);

  const description = queryParams.get("error_description") ?? hashParams.get("error_description");
  if (description) return description;

  const code = queryParams.get("error") ?? hashParams.get("error");
  if (code) return code;

  return null;
}
