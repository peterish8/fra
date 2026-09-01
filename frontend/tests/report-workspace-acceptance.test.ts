import { describe, expect, it } from "vitest";

import { createAuthenticatedApiClient } from "../lib/auth/api-client";
import { FixtureReportBackend } from "./fixtures/report-workspace-backend";
import libraryFixture from "./fixtures/report-workspace-library.json";

const API_BASE_URL = "http://api.fixture.test";
const ACCESS_TOKEN = "fixture-owner-access-token";
const REQUEST_ID = "req_frontend_fixture_001";

type FixtureReport = (typeof libraryFixture.items)[number];

type ReportApiClient = ReturnType<typeof createAuthenticatedApiClient> & {
  delete<T>(path: string, options?: { headers?: HeadersInit }): Promise<T>;
};

function makeReportClient(backend: FixtureReportBackend): ReportApiClient {
  return createAuthenticatedApiClient({
    accessToken: ACCESS_TOKEN,
    baseUrl: API_BASE_URL,
    fetchImplementation: backend.fetch.bind(backend),
  }) as ReportApiClient;
}

describe("report creation, library, and sidebar acceptance at the backend boundary", () => {
  it("submits creation fields and exposes the returned stable DRAFT workspace", async () => {
    const backend = new FixtureReportBackend();
    const client = makeReportClient(backend);
    const payload = {
      title: "Apple - Financial Health",
      subject: { query: "Apple", country_code: "US", ticker: "AAPL" },
      focus: ["financials", "disclosure"],
      depth: "STANDARD",
    };

    const created = await client.post<typeof libraryFixture.created>("/v1/reports", payload, {
      headers: { "Idempotency-Key": "create-apple-001", "X-Request-ID": REQUEST_ID },
    });

    expect(created).toEqual(libraryFixture.created);
    expect(backend.requests[0]).toMatchObject({
      method: "POST",
      url: `${API_BASE_URL}/v1/reports`,
      body: payload,
    });
    expect(backend.requests[0]?.headers.get("Authorization")).toBe(`Bearer ${ACCESS_TOKEN}`);
    expect(backend.requests[0]?.headers.get("Idempotency-Key")).toBe("create-apple-001");
  });

  it("loads a search/status-filtered library and maps only returned workspaces into the sidebar", async () => {
    const backend = new FixtureReportBackend();
    const client = makeReportClient(backend);

    const page = await client.get<typeof libraryFixture>("/v1/reports?q=nvidia&status=DRAFT");
    const sidebarItems = page.items.map(({ report_id, title, status }) => ({ report_id, title, status }));

    expect(sidebarItems).toEqual([
      {
        report_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        title: "NVIDIA - Deep Research",
        status: "DRAFT",
      },
    ]);
    expect(sidebarItems).not.toContainEqual(
      expect.objectContaining({ report_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd" }),
    );
    expect(backend.requests[0]?.url).toBe(`${API_BASE_URL}/v1/reports?q=nvidia&status=DRAFT`);
  });

  it("opens a selected report and represents an empty library without inventing items", async () => {
    const backend = new FixtureReportBackend();
    const client = makeReportClient(backend);

    const opened = await client.get<FixtureReport>(
      "/v1/reports/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    );
    const empty = await client.get<typeof libraryFixture>("/v1/reports?q=does-not-exist");

    expect(opened.report_id).toBe("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    expect(empty.items).toEqual([]);
    expect(empty.next_cursor).toBeNull();
  });

  it("deletes through the authenticated boundary and removes the workspace from the next sidebar read", async () => {
    const backend = new FixtureReportBackend();
    const client = makeReportClient(backend);

    await client.delete<void>("/v1/reports/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", {
      headers: { "X-Request-ID": REQUEST_ID },
    });
    const page = await client.get<typeof libraryFixture>("/v1/reports");

    expect(page.items).toEqual([libraryFixture.items[1]]);
    expect(backend.requests[0]?.headers.get("Authorization")).toBe(`Bearer ${ACCESS_TOKEN}`);
  });

  it("surfaces stable backend errors as human-readable client errors", async () => {
    const backend = new FixtureReportBackend();
    const client = makeReportClient(backend);

    await expect(
      client.get("/v1/reports/ffffffff-ffff-4fff-8fff-ffffffffffff"),
    ).rejects.toMatchObject({
      status: 404,
      message: "The report workspace was not found.",
    });
  });
});
