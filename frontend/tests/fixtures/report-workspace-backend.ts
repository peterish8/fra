import libraryFixture from "./report-workspace-library.json";

type FixtureReport = (typeof libraryFixture.items)[number];

export class FixtureReportBackend {
  readonly requests: Array<{ method: string; url: string; headers: Headers; body?: unknown }> = [];
  private reports: FixtureReport[] = [...libraryFixture.items];

  async fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const url = String(input);
    const method = init?.method ?? "GET";
    const headers = new Headers(init?.headers);
    const body = init?.body === undefined ? undefined : JSON.parse(String(init.body));
    this.requests.push({ method, url, headers, body });

    const path = new URL(url).pathname;
    if (method === "POST" && path === "/v1/reports") {
      return this.json(libraryFixture.created, 201);
    }

    if (method === "GET" && path === "/v1/reports") {
      const query = new URL(url).searchParams.get("q")?.toLowerCase();
      const status = new URL(url).searchParams.get("status");
      const items = this.reports.filter(
        (report) =>
          (!query || report.title.toLowerCase().includes(query)) &&
          (!status || report.status === status),
      );
      return this.json({ items, next_cursor: null });
    }

    if (method === "GET" && path.startsWith("/v1/reports/")) {
      const reportId = path.split("/").pop();
      const report = this.reports.find((item) => item.report_id === reportId);
      return report === undefined
        ? this.error(404, "NOT_FOUND", "The report workspace was not found.")
        : this.json(report);
    }

    if (method === "DELETE" && path.startsWith("/v1/reports/")) {
      const reportId = path.split("/").pop();
      this.reports = this.reports.filter((item) => item.report_id !== reportId);
      return new Response(null, { status: 204 });
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
    return this.json(
      { error: { code, message, request_id: "req_frontend_fixture_001" } },
      status,
    );
  }
}
