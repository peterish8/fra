import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it, vi } from "vitest";

import providerSecretNames from "./fixtures/provider-secret-names.json";
import { createAuthenticatedApiClient } from "../lib/auth/api-client";

const API_BASE_URL = "http://api.fixture.test";
const ACCESS_TOKEN = "fixture-user-access-token";

describe("authenticated frontend API boundary", () => {
  it("sends the user bearer token only to the configured backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "fixture-user" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = createAuthenticatedApiClient({
      accessToken: ACCESS_TOKEN,
      baseUrl: API_BASE_URL,
    });

    await client.get("/v1/me");

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/v1/me`,
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: `Bearer ${ACCESS_TOKEN}`,
        }),
      }),
    );
    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    const requestHeaders = new Headers(requestInit?.headers);
    expect(requestHeaders.get("Authorization")).toBe(`Bearer ${ACCESS_TOKEN}`);
    expect(requestHeaders.get("X-Provider-Api-Key")).toBeNull();
    expect(requestHeaders.get("X-Supabase-Service-Role-Key")).toBeNull();
  });

  it("does not reference server-only provider secrets anywhere in frontend lib", () => {
    const frontendLib = resolve(__dirname, "../lib");
    const clientSource = readFileSync(
      resolve(frontendLib, "auth/api-client.ts"),
      "utf8",
    );

    for (const secretName of providerSecretNames) {
      expect(clientSource).not.toContain(secretName);
    }
    expect(clientSource).not.toMatch(/process\.env\.[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)/);
  });
});
