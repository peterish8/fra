import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export class SupabaseNotConfiguredError extends Error {
  constructor() {
    super("Supabase is not configured for this environment.");
    this.name = "SupabaseNotConfiguredError";
  }
}

let cachedClient: SupabaseClient | null = null;

export function isSupabaseConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() &&
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim(),
  );
}

/**
 * A browser-only Supabase client for Supabase Auth. It never receives a
 * service-role key or other server secret, only the public anon key.
 */
export function getSupabaseBrowserClient(): SupabaseClient {
  if (cachedClient) return cachedClient;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();

  if (!url || !anonKey) {
    throw new SupabaseNotConfiguredError();
  }

  cachedClient = createClient(url, anonKey, {
    auth: { persistSession: true, autoRefreshToken: true },
  });
  return cachedClient;
}
