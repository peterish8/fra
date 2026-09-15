import { mapAuthErrorMessage } from "./auth-error-message";

export const RESEND_COOLDOWN_SECONDS = 30;

type OtpAuthError = { message: string; code?: string } | null;

/**
 * The slice of a Supabase client these functions need. Kept minimal (rather
 * than the full `SupabaseClient` type) so tests can pass a plain mock without
 * implementing the entire auth client surface; the real client's methods are
 * a structural superset and satisfy this without a cast.
 */
type AuthOnly = {
  auth: {
    signInWithOtp: (credentials: {
      email: string;
      options?: { shouldCreateUser?: boolean };
    }) => Promise<{ error: OtpAuthError }>;
    verifyOtp: (params: {
      email: string;
      token: string;
      type: "email";
    }) => Promise<{ error: OtpAuthError }>;
  };
};

export type OtpActionResult = { ok: true } | { ok: false; message: string };

export function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export function isValidOtpCode(value: string): boolean {
  return /^\d{6}$/.test(value.trim());
}

/** Seconds left on the resend cooldown, given when it ends and the current time. */
export function secondsUntil(cooldownEndsAt: number | null, now: number): number {
  if (cooldownEndsAt === null) return 0;
  return Math.max(0, Math.ceil((cooldownEndsAt - now) / 1000));
}

/**
 * Request a login code by email. Restricted to emails that already have an
 * account: unknown addresses get a clear error rather than silently signing up.
 */
export async function sendLoginCode(supabase: AuthOnly, email: string): Promise<OtpActionResult> {
  const trimmedEmail = email.trim();
  if (!isValidEmail(trimmedEmail)) {
    return { ok: false, message: "Enter a valid email address." };
  }

  const { error } = await supabase.auth.signInWithOtp({
    email: trimmedEmail,
    options: { shouldCreateUser: false },
  });
  if (error) return { ok: false, message: mapAuthErrorMessage(error) };
  return { ok: true };
}

/**
 * Request a signup code by email. Open to anyone: an unknown address gets a
 * new account created for it. Verifying the resulting code is identical to
 * login, handled by `verifyLoginCode`.
 */
export async function sendSignUpCode(supabase: AuthOnly, email: string): Promise<OtpActionResult> {
  const trimmedEmail = email.trim();
  if (!isValidEmail(trimmedEmail)) {
    return { ok: false, message: "Enter a valid email address." };
  }

  const { error } = await supabase.auth.signInWithOtp({
    email: trimmedEmail,
    options: { shouldCreateUser: true },
  });
  if (error) return { ok: false, message: mapAuthErrorMessage(error) };
  return { ok: true };
}

export async function verifyLoginCode(
  supabase: AuthOnly,
  email: string,
  code: string,
): Promise<OtpActionResult> {
  const trimmedCode = code.trim();
  if (!isValidOtpCode(trimmedCode)) {
    return { ok: false, message: "Enter the 6-digit code from your email." };
  }

  const { error } = await supabase.auth.verifyOtp({
    email: email.trim(),
    token: trimmedCode,
    type: "email",
  });
  if (error) return { ok: false, message: mapAuthErrorMessage(error) };
  return { ok: true };
}
