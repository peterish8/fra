import { createElement, type ComponentType } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { createAuthenticatedApiClient } from "../lib/auth/api-client";
import uiFixture from "./fixtures/entity-resolution-ui.json";

const API_BASE_URL = "http://api.fixture.test";
const ACCESS_TOKEN = "fixture-owner-access-token";
const REPORT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

type FixtureResolution = (typeof uiFixture.ambiguous) | (typeof uiFixture.unconfirmed) | (typeof uiFixture.resolved);

class FixtureEntityBackend {
  readonly requests: Array<{ method: string; url: string; body?: unknown; headers: Headers }> = [];

  async fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const url = String(input);
    const method = init?.method ?? "GET";
    const headers = new Headers(init?.headers);
    const body = init?.body === undefined ? undefined : JSON.parse(String(init.body));
    this.requests.push({ method, url, body, headers });
    const path = new URL(url).pathname;

    if (method === "POST" && path === "/v1/companies/resolve") {
      const query = typeof body?.query === "string" ? body.query : "";
      if (query === "Meridian Foods") return this.json(uiFixture.ambiguous);
      if (query === "Quiet Meadow AI") return this.json(uiFixture.unconfirmed);
      return this.json(uiFixture.resolved);
    }

    if (method === "POST" && path === `/v1/reports/${REPORT_ID}/research-runs`) {
      if (body?.company_id !== uiFixture.resolved.selected_company_id) {
        return this.error(409, "ENTITY_AMBIGUOUS", "Choose a legal entity before research begins.");
      }
      return this.json({ research_run_id: "run-entity-001", status: "QUEUED" }, 202);
    }

    return this.error(404, "NOT_FOUND", "The requested fixture route was not found.");
  }

  private json(payload: unknown, status = 200): Response {
    return new Response(JSON.stringify(payload), {
      status,
      headers: { "content-type": "application/json" },
    });
  }

  private error(status: number, code: string, message: string): Response {
    return this.json({ error: { code, message, request_id: "req_entity_frontend_001" } }, status);
  }
}

function makeClient(backend: FixtureEntityBackend) {
  return createAuthenticatedApiClient({
    accessToken: ACCESS_TOKEN,
    baseUrl: API_BASE_URL,
    fetchImplementation: backend.fetch.bind(backend),
  });
}

describe("entity resolution acceptance at the authenticated backend boundary", () => {
  it("returns candidates with status, confidence, reasons, and legal evidence metadata", async () => {
    const backend = new FixtureEntityBackend();
    const client = makeClient(backend);

    const resolution = await client.post<FixtureResolution>("/v1/companies/resolve", {
      query: "Meridian Foods",
    });

    expect(resolution.status).toBe("AMBIGUOUS");
    expect(resolution.selected_company_id).toBeNull();
    expect(resolution.research_allowed).toBe(false);
    expect(resolution.abstention_reason).toBeTruthy();
    expect(resolution.candidates).toHaveLength(2);
    expect(resolution.candidates[0]).toMatchObject({
      canonical_name: "Meridian Foods Limited",
      country_code: "IN",
      confidence: 0.74,
    });
    expect(resolution.candidates[0]?.match_reasons[0]?.detail).toBeTruthy();
    expect(resolution.candidates[0]?.evidence_refs).toEqual(["registry-mca-meridian-001"]);
    expect(backend.requests[0]?.headers.get("Authorization")).toBe(`Bearer ${ACCESS_TOKEN}`);
  });

  it("does not permit expensive research until an explicit company ID is selected", async () => {
    const backend = new FixtureEntityBackend();
    const client = makeClient(backend);
    const resolution = await client.post<FixtureResolution>("/v1/companies/resolve", {
      query: "Meridian Foods",
    });

    expect(resolution.research_allowed).toBe(false);
    await expect(
      client.post(`/v1/reports/${REPORT_ID}/research-runs`, { depth: "DEEP" }),
    ).rejects.toMatchObject({
      status: 409,
      message: "Choose a legal entity before research begins.",
    });

    const queued = await client.post<{ status: string }>(
      `/v1/reports/${REPORT_ID}/research-runs`,
      { depth: "DEEP", company_id: uiFixture.resolved.selected_company_id },
    );
    expect(queued.status).toBe("QUEUED");
    expect(backend.requests.at(-1)?.body).toEqual({
      depth: "DEEP",
      company_id: uiFixture.resolved.selected_company_id,
    });
  });

  it("renders unconfirmed identity as an actionable state rather than a negative verdict", async () => {
    const backend = new FixtureEntityBackend();
    const client = makeClient(backend);
    const resolution = await client.post<FixtureResolution>("/v1/companies/resolve", {
      query: "Quiet Meadow AI",
    });

    expect(resolution.status).toBe("UNCONFIRMED");
    expect(resolution.candidates).toEqual([]);
    expect(resolution.abstention_reason).toContain("Not enough identity evidence");
    expect(resolution.research_allowed).toBe(false);
    expect(resolution.status).not.toMatch(/fake|fraud|false/i);
  });

  it("exposes candidate choice and both ambiguity and unconfirmed states through accessible status affordances", async () => {
    const componentModulePath = "../components/entity/entity-resolution-panel";
    let entityModule: Record<string, unknown>;
    try {
      // @vite-ignore keeps this red contract executable when the planned component is absent.
      entityModule = (await import(componentModulePath)) as Record<string, unknown>;
    } catch (error) {
      throw new Error(`missing frontend entity-resolution behavior: ${String(error)}`);
    }

    const panel = entityModule.EntityResolutionPanel ?? entityModule.default;
    expect(typeof panel).toBe("function");
    const ambiguousMarkup = renderToStaticMarkup(
      createElement(panel as ComponentType<Record<string, unknown>>, {
        resolution: uiFixture.ambiguous,
        onSelect: () => undefined,
      }),
    );

    expect(ambiguousMarkup).toContain("Choose the legal entity");
    expect(ambiguousMarkup).toContain("Meridian Foods Limited");
    expect(ambiguousMarkup).toContain("Meridian Foods, Inc.");
    expect(ambiguousMarkup).toMatch(/74%|0\.74/);
    expect(ambiguousMarkup).toMatch(/Ambiguous|Choose/i);
    expect(ambiguousMarkup).toMatch(/aria-label=|role=|aria-live=/);
    expect(ambiguousMarkup).toMatch(/button|checkbox|radio/i);

    const unconfirmedMarkup = renderToStaticMarkup(
      createElement(panel as ComponentType<Record<string, unknown>>, {
        resolution: uiFixture.unconfirmed,
        onSelect: () => undefined,
      }),
    );
    expect(unconfirmedMarkup).toContain("Not enough identity evidence");
    expect(unconfirmedMarkup).toMatch(/Unconfirmed|Insufficient evidence/i);
    expect(unconfirmedMarkup).toMatch(/aria-label=|role=|aria-live=/);
  });
});
