import { describe, expect, it, vi } from "vitest";

import {
  RESEND_COOLDOWN_SECONDS,
  isValidEmail,
  isValidOtpCode,
  secondsUntil,
  sendLoginCode,
  sendSignUpCode,
  verifyLoginCode,
} from "../lib/auth/otp-login";

type FakeAuthError = { message: string; code?: string } | null;

function fakeSupabase(overrides: {
  signInWithOtp?: () => Promise<{ error: FakeAuthError }>;
  verifyOtp?: () => Promise<{ error: FakeAuthError }>;
}) {
  return {
    auth: {
      signInWithOtp: vi.fn(overrides.signInWithOtp ?? (async () => ({ error: null }))),
      verifyOtp: vi.fn(overrides.verifyOtp ?? (async () => ({ error: null }))),
    },
  };
}

describe("isValidEmail", () => {
  it("accepts a plausible email address", () => {
    expect(isValidEmail("researcher@example.com")).toBe(true);
  });

  it("rejects empty or malformed input", () => {
    expect(isValidEmail("")).toBe(false);
    expect(isValidEmail("   ")).toBe(false);
    expect(isValidEmail("not-an-email")).toBe(false);
  });
});

describe("isValidOtpCode", () => {
  it("accepts exactly six digits", () => {
    expect(isValidOtpCode("123456")).toBe(true);
    expect(isValidOtpCode(" 123456 ")).toBe(true);
  });

  it("rejects anything else", () => {
    expect(isValidOtpCode("12345")).toBe(false);
    expect(isValidOtpCode("1234567")).toBe(false);
    expect(isValidOtpCode("12a456")).toBe(false);
    expect(isValidOtpCode("")).toBe(false);
  });
});

describe("secondsUntil", () => {
  it("returns 0 when there is no active cooldown", () => {
    expect(secondsUntil(null, Date.now())).toBe(0);
  });

  it("counts down and never goes negative", () => {
    const now = 1_000_000;
    expect(secondsUntil(now + 12_400, now)).toBe(13);
    expect(secondsUntil(now - 5_000, now)).toBe(0);
  });
});

describe("sendLoginCode", () => {
  it("rejects an invalid email before calling Supabase", async () => {
    const supabase = fakeSupabase({});
    const result = await sendLoginCode(supabase, "not-an-email");
    expect(result).toEqual({ ok: false, message: "Enter a valid email address." });
    expect(supabase.auth.signInWithOtp).not.toHaveBeenCalled();
  });

  it("requests a code without allowing new-account signup", async () => {
    const supabase = fakeSupabase({});
    const result = await sendLoginCode(supabase, "researcher@example.com");

    expect(result).toEqual({ ok: true });
    expect(supabase.auth.signInWithOtp).toHaveBeenCalledWith({
      email: "researcher@example.com",
      options: { shouldCreateUser: false },
    });
  });

  it("maps a Supabase error to researcher-facing copy", async () => {
    const supabase = fakeSupabase({
      signInWithOtp: async () => ({
        error: { message: "Email rate limit exceeded", code: "over_email_send_rate_limit" },
      }),
    });
    const result = await sendLoginCode(supabase, "researcher@example.com");
    expect(result).toEqual({ ok: false, message: "Too many attempts. Wait a moment and try again." });
  });
});

describe("sendSignUpCode", () => {
  it("rejects an invalid email before calling Supabase", async () => {
    const supabase = fakeSupabase({});
    const result = await sendSignUpCode(supabase, "not-an-email");
    expect(result).toEqual({ ok: false, message: "Enter a valid email address." });
    expect(supabase.auth.signInWithOtp).not.toHaveBeenCalled();
  });

  it("requests a code that allows new-account signup", async () => {
    const supabase = fakeSupabase({});
    const result = await sendSignUpCode(supabase, "newresearcher@example.com");

    expect(result).toEqual({ ok: true });
    expect(supabase.auth.signInWithOtp).toHaveBeenCalledWith({
      email: "newresearcher@example.com",
      options: { shouldCreateUser: true },
    });
  });

  it("maps a Supabase error to the same researcher-facing copy as login", async () => {
    const supabase = fakeSupabase({
      signInWithOtp: async () => ({
        error: { message: "Email rate limit exceeded", code: "over_email_send_rate_limit" },
      }),
    });
    const result = await sendSignUpCode(supabase, "newresearcher@example.com");
    expect(result).toEqual({ ok: false, message: "Too many attempts. Wait a moment and try again." });
  });

  it("finishing a signup with an expired code maps the same way login does (shared verifyLoginCode)", async () => {
    const supabase = fakeSupabase({
      verifyOtp: async () => ({
        error: { message: "Token has expired or is invalid", code: "otp_expired" },
      }),
    });
    const result = await verifyLoginCode(supabase, "newresearcher@example.com", "123456");
    expect(result).toEqual({
      ok: false,
      message: "That code isn't valid or has expired. Request a new one and try again.",
    });
  });
});

describe("verifyLoginCode", () => {
  it("rejects a malformed code before calling Supabase", async () => {
    const supabase = fakeSupabase({});
    const result = await verifyLoginCode(supabase, "researcher@example.com", "12ab");
    expect(result).toEqual({ ok: false, message: "Enter the 6-digit code from your email." });
    expect(supabase.auth.verifyOtp).not.toHaveBeenCalled();
  });

  it("verifies a well-formed code against Supabase", async () => {
    const supabase = fakeSupabase({});
    const result = await verifyLoginCode(supabase, "researcher@example.com", "123456");

    expect(result).toEqual({ ok: true });
    expect(supabase.auth.verifyOtp).toHaveBeenCalledWith({
      email: "researcher@example.com",
      token: "123456",
      type: "email",
    });
  });

  it("maps an expired/invalid code error to researcher-facing copy", async () => {
    const supabase = fakeSupabase({
      verifyOtp: async () => ({
        error: { message: "Token has expired or is invalid", code: "otp_expired" },
      }),
    });
    const result = await verifyLoginCode(supabase, "researcher@example.com", "123456");
    expect(result).toEqual({
      ok: false,
      message: "That code isn't valid or has expired. Request a new one and try again.",
    });
  });
});

describe("RESEND_COOLDOWN_SECONDS", () => {
  it("is the 30-second cooldown the product spec calls for", () => {
    expect(RESEND_COOLDOWN_SECONDS).toBe(30);
  });
});
