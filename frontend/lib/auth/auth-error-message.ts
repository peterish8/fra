import { SupabaseNotConfiguredError } from "./supabase-browser-client";

type AuthErrorLike = { message: string; code?: string };

function asAuthErrorLike(error: unknown): AuthErrorLike | null {
  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof (error as { message: unknown }).message === "string"
  ) {
    const code = "code" in error ? (error as { code: unknown }).code : undefined;
    return {
      message: (error as { message: string }).message,
      code: typeof code === "string" ? code : undefined,
    };
  }
  return null;
}

/** Map a Supabase Auth error (or anything else thrown during email-code sign-in) to copy a researcher can act on. */
export function mapAuthErrorMessage(error: unknown): string {
  if (error instanceof SupabaseNotConfiguredError) {
    return "Sign-in isn't configured for this environment yet. Add Supabase credentials and try again.";
  }

  const authError = asAuthErrorLike(error);
  if (authError === null) {
    return "Something went wrong while signing in. Please try again.";
  }

  switch (authError.code) {
    case "otp_expired":
      return "That code isn't valid or has expired. Request a new one and try again.";
    case "over_email_send_rate_limit":
    case "over_request_rate_limit":
      return "Too many attempts. Wait a moment and try again.";
    case "email_address_invalid":
      return "Enter a valid email address.";
    case "otp_disabled":
    case "email_provider_disabled":
    case "signup_disabled":
      return "Email sign-in isn't available for this project right now.";
    default:
      break;
  }

  const { message } = authError;
  if (/token.*(expired|invalid)|invalid.*(otp|token|code)/i.test(message)) {
    return "That code isn't valid or has expired. Request a new one and try again.";
  }
  if (/rate limit|too many/i.test(message)) {
    return "Too many attempts. Wait a moment and try again.";
  }
  return message;
}
