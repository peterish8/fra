import { describe, expect, it, vi } from "vitest";

import { extractOAuthErrorFromUrl, signInWithGoogle } from "../lib/auth/oauth-login";

type FakeOAuthError = { message: string; code?: string } | null;

function fakeSupabase(overrides: {
  signInWithOAuth?: () => Promise<{ error: FakeOAuthError }>;
}) {
  return {
    auth: {
      signInWithOAuth: vi.fn(overrides.signInWithOAuth ?? (async () => ({ error: null }))),
    },
  };
}

describe("signInWithGoogle", () => {
  it("starts the Google OAuth redirect with the given return URL", async () => {
    const supabase = fakeSupabase({});
    const result = await signInWithGoogle(supabase, "http://localhost:3000/auth/callback");

    expect(result).toEqual({ ok: true });
    expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: "http://localhost:3000/auth/callback" },
    });
  });

  it("maps a Supabase error to researcher-facing copy", async () => {
    const supabase = fakeSupabase({
      signInWithOAuth: async () => ({
        error: { message: "Unsupported provider: provider is not enabled", code: "email_provider_disabled" },
      }),
    });
    const result = await signInWithGoogle(supabase, "http://localhost:3000/auth/callback");
    expect(result).toEqual({
      ok: false,
      message: "Email sign-in isn't available for this project right now.",
    });
  });
});

describe("extractOAuthErrorFromUrl", () => {
  it("returns null when there is no error in the URL", () => {
    expect(extractOAuthErrorFromUrl("", "")).toBeNull();
    expect(extractOAuthErrorFromUrl("?code=abc123", "")).toBeNull();
  });

  it("prefers a query-string error_description over a bare error code", () => {
    expect(
      extractOAuthErrorFromUrl("?error=access_denied&error_description=User+cancelled", ""),
    ).toBe("User cancelled");
  });

  it("falls back to the bare error code when no description is present", () => {
    expect(extractOAuthErrorFromUrl("?error=access_denied", "")).toBe("access_denied");
  });

  it("reads the error from a hash fragment (implicit-flow style)", () => {
    expect(
      extractOAuthErrorFromUrl("", "#error=server_error&error_description=Something+broke"),
    ).toBe("Something broke");
  });

  it("prefers a query-string error over a hash-fragment error", () => {
    expect(
      extractOAuthErrorFromUrl(
        "?error_description=From+query",
        "#error_description=From+hash",
      ),
    ).toBe("From query");
  });
});
