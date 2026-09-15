import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("getSupabaseBrowserClient", () => {
  it("throws SupabaseNotConfiguredError when credentials are missing", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");
    const { getSupabaseBrowserClient, SupabaseNotConfiguredError } = await import(
      "../lib/auth/supabase-browser-client"
    );

    expect(() => getSupabaseBrowserClient()).toThrow(SupabaseNotConfiguredError);
  });

  it("reports configured only when both values are present", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://project.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");
    const { isSupabaseConfigured } = await import("../lib/auth/supabase-browser-client");
    expect(isSupabaseConfigured()).toBe(false);
  });

  it("builds and caches a single client once credentials are present", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://project.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "fixture-anon-key");
    const { getSupabaseBrowserClient, isSupabaseConfigured } = await import(
      "../lib/auth/supabase-browser-client"
    );

    expect(isSupabaseConfigured()).toBe(true);
    const first = getSupabaseBrowserClient();
    const second = getSupabaseBrowserClient();
    expect(first).toBe(second);
  });
});
