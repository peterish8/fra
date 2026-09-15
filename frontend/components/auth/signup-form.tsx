"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  RESEND_COOLDOWN_SECONDS,
  secondsUntil,
  sendSignUpCode,
  verifyLoginCode,
} from "@/lib/auth/otp-login";
import { signInWithGoogle } from "@/lib/auth/oauth-login";
import { getSupabaseBrowserClient } from "@/lib/auth/supabase-browser-client";
import { mapAuthErrorMessage } from "@/lib/auth/auth-error-message";
import { GoogleIcon } from "./google-icon";

type Status =
  | { state: "idle" }
  | { state: "sending-code" }
  | { state: "code-sent" }
  | { state: "verifying" }
  | { state: "redirecting" }
  | { state: "error"; message: string }
  | { state: "success" };

export function SignupForm() {
  const router = useRouter();
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<Status>({ state: "idle" });
  const [cooldownEndsAt, setCooldownEndsAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const isBusy =
    status.state === "sending-code" || status.state === "verifying" || status.state === "redirecting";
  const cooldownSeconds = secondsUntil(cooldownEndsAt, now);

  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [cooldownSeconds]);

  function getClientOrError() {
    try {
      return getSupabaseBrowserClient();
    } catch (error) {
      setStatus({ state: "error", message: mapAuthErrorMessage(error) });
      return null;
    }
  }

  async function handleSendCode(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isBusy) return;

    const supabase = getClientOrError();
    if (!supabase) return;

    setStatus({ state: "sending-code" });
    const result = await sendSignUpCode(supabase, email);
    if (!result.ok) {
      setStatus({ state: "error", message: result.message });
      return;
    }
    setStatus({ state: "code-sent" });
    setStep("code");
    setCooldownEndsAt(Date.now() + RESEND_COOLDOWN_SECONDS * 1000);
    setNow(Date.now());
  }

  async function handleVerify(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isBusy) return;

    const supabase = getClientOrError();
    if (!supabase) return;

    setStatus({ state: "verifying" });
    const result = await verifyLoginCode(supabase, email, code);
    if (!result.ok) {
      setStatus({ state: "error", message: result.message });
      return;
    }
    setStatus({ state: "success" });
    router.push("/research");
  }

  async function handleResend() {
    if (isBusy || cooldownSeconds > 0) return;

    const supabase = getClientOrError();
    if (!supabase) return;

    setStatus({ state: "sending-code" });
    const result = await sendSignUpCode(supabase, email);
    if (!result.ok) {
      setStatus({ state: "error", message: result.message });
      return;
    }
    setStatus({ state: "code-sent" });
    setCooldownEndsAt(Date.now() + RESEND_COOLDOWN_SECONDS * 1000);
    setNow(Date.now());
  }

  function handleUseDifferentEmail() {
    if (isBusy) return;
    setStep("email");
    setCode("");
    setCooldownEndsAt(null);
    setStatus({ state: "idle" });
  }

  async function handleGoogleSignIn() {
    if (isBusy) return;

    const supabase = getClientOrError();
    if (!supabase) return;

    setStatus({ state: "redirecting" });
    const result = await signInWithGoogle(supabase, `${window.location.origin}/auth/callback`);
    if (!result.ok) {
      setStatus({ state: "error", message: result.message });
    }
    // On success the browser navigates away to Google; nothing else to do here.
  }

  const errorMessage = status.state === "error" ? status.message : null;

  return (
    <main className="auth-screen">
      <form
        className="auth-card"
        onSubmit={step === "email" ? handleSendCode : handleVerify}
        noValidate
      >
        <div className="dev-auth-mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <p className="auth-kicker">Sign up</p>
        <h1>Create your research desk account.</h1>

        {step === "email" ? (
          <>
            <p className="auth-subtitle">
              Enter your email and we&apos;ll send you a 6-digit code to create your account.
            </p>
            <div className="auth-field">
              <label htmlFor="signup-email">Email</label>
              <input
                id="signup-email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="auth-input"
                value={email}
                disabled={isBusy}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>

            {errorMessage ? (
              <p className="auth-error" role="alert">
                {errorMessage}
              </p>
            ) : null}

            <button type="submit" className="auth-button" disabled={isBusy}>
              {status.state === "sending-code" ? "Sending code…" : "Send code"}
              <span aria-hidden="true">→</span>
            </button>
            <small>You&apos;ll receive a 6-digit code by email — no password required.</small>

            <div className="auth-divider">or</div>
            <button
              type="button"
              className="auth-button-secondary"
              onClick={handleGoogleSignIn}
              disabled={isBusy}
            >
              <GoogleIcon />
              {status.state === "redirecting" ? "Redirecting…" : "Continue with Google"}
            </button>
          </>
        ) : (
          <>
            <p className="auth-subtitle">
              We sent a 6-digit code to <strong>{email}</strong>. Enter it below to create your
              account and sign in.
            </p>
            <div className="auth-field">
              <label htmlFor="signup-code">6-digit code</label>
              <input
                id="signup-code"
                name="code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                autoComplete="one-time-code"
                required
                className="auth-input"
                value={code}
                disabled={isBusy}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
              />
            </div>

            {errorMessage ? (
              <p className="auth-error" role="alert">
                {errorMessage}
              </p>
            ) : null}

            <button type="submit" className="auth-button" disabled={isBusy}>
              {status.state === "verifying" ? "Verifying…" : "Verify & create account"}
              <span aria-hidden="true">→</span>
            </button>

            <div className="auth-field-row">
              <button
                type="button"
                className="text-link"
                onClick={handleResend}
                disabled={isBusy || cooldownSeconds > 0}
              >
                {cooldownSeconds > 0 ? `Resend code (${cooldownSeconds}s)` : "Resend code"}
              </button>
              <button
                type="button"
                className="text-link"
                onClick={handleUseDifferentEmail}
                disabled={isBusy}
              >
                Use a different email
              </button>
            </div>
          </>
        )}

        <small>
          Already have an account? <Link href="/login" className="text-link">Sign in</Link>
        </small>
      </form>
    </main>
  );
}
