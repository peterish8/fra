import { describe, expect, it } from "vitest";

import { mapAuthErrorMessage } from "../lib/auth/auth-error-message";
import { SupabaseNotConfiguredError } from "../lib/auth/supabase-browser-client";

describe("mapAuthErrorMessage", () => {
  it("gives actionable copy when Supabase credentials are missing", () => {
    expect(mapAuthErrorMessage(new SupabaseNotConfiguredError())).toMatch(/isn't configured/i);
  });

  it("translates an expired-or-invalid code by error code", () => {
    expect(mapAuthErrorMessage({ message: "Token has expired or is invalid", code: "otp_expired" })).toMatch(
      /isn't valid or has expired/i,
    );
  });

  it("translates an expired-or-invalid code from message text alone (no code field)", () => {
    expect(mapAuthErrorMessage({ message: "Token has expired or is invalid" })).toMatch(
      /isn't valid or has expired/i,
    );
  });

  it("translates rate-limit errors by error code", () => {
    expect(
      mapAuthErrorMessage({ message: "Email rate limit exceeded", code: "over_email_send_rate_limit" }),
    ).toMatch(/too many attempts/i);
    expect(
      mapAuthErrorMessage({ message: "Request rate limit reached", code: "over_request_rate_limit" }),
    ).toMatch(/too many attempts/i);
  });

  it("translates rate-limit errors from message text alone", () => {
    expect(mapAuthErrorMessage({ message: "Email rate limit exceeded" })).toMatch(/too many attempts/i);
  });

  it("translates an invalid email address error", () => {
    expect(mapAuthErrorMessage({ message: "Unable to validate email address", code: "email_address_invalid" })).toMatch(
      /valid email address/i,
    );
  });

  it("translates disabled-email-signin errors", () => {
    expect(mapAuthErrorMessage({ message: "Signups not allowed for this instance", code: "otp_disabled" })).toMatch(
      /isn't available for this project/i,
    );
    expect(
      mapAuthErrorMessage({ message: "Email logins are disabled", code: "email_provider_disabled" }),
    ).toMatch(/isn't available for this project/i);
  });

  it("passes through any other Supabase error message unchanged", () => {
    expect(mapAuthErrorMessage({ message: "Something unexpected happened upstream" })).toBe(
      "Something unexpected happened upstream",
    );
  });

  it("falls back to generic copy for a non-error-shaped throw", () => {
    expect(mapAuthErrorMessage("boom")).toMatch(/something went wrong/i);
    expect(mapAuthErrorMessage(undefined)).toMatch(/something went wrong/i);
  });
});
