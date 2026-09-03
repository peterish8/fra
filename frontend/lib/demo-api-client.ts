import type {
  CreateReportRequest,
  ReportApiClient,
  ReportDetail,
  ReportListResponse,
  ReportSummary,
} from "@/components/research/research-types";

let demoReports: ReportSummary[] = [
  { report_id: "rpt-nvidia", title: "NVIDIA · Full Research", status: "VERIFIED", current_version: 3, updated_at: "2026-08-28T09:20:00Z", subject: { query: "NVIDIA", country_code: "US", ticker: "NVDA", domain: "nvidia.com" }, focus: ["full_research"], depth: "DEEP" },
  { report_id: "rpt-shopify", title: "Shopify · Growth and risks", status: "RESEARCHING", current_version: 1, updated_at: "2026-08-31T14:05:00Z", subject: { query: "Shopify", country_code: "CA", ticker: "SHOP", domain: "shopify.com" }, focus: ["growth", "risks"], depth: "STANDARD" },
  { report_id: "rpt-stripe", title: "Stripe · Disclosure check", status: "DRAFT", current_version: null, updated_at: "2026-09-01T11:40:00Z", subject: { query: "Stripe", country_code: "US", domain: "stripe.com" }, focus: ["disclosure"], depth: "FAST" },
];

function detail(report: ReportSummary): ReportDetail {
  return {
    ...report,
    company: { canonical_name: report.subject?.query, resolution_status: "RESOLVED", legal_entity: "Demo fixture company" },
    quality: { research_confidence: 92, disclosure_reliability: 78, financial_business_score: 84 },
  };
}

export const demoReportApiClient: ReportApiClient = {
  async get<T>(path: string): Promise<T> {
    if (path.startsWith("/v1/reports/") && !path.includes("?")) {
      const id = decodeURIComponent(path.split("/").pop() ?? "");
      const report = demoReports.find((item) => item.report_id === id);
      if (!report) throw new Error("This demo workspace no longer exists.");
      return detail(report) as T;
    }

    const [, queryString = ""] = path.split("?");
    const params = new URLSearchParams(queryString);
    const query = params.get("q")?.toLowerCase() ?? "";
    const status = params.get("status") ?? "";
    const items = demoReports.filter((report) =>
      (!query || report.title.toLowerCase().includes(query) || report.subject?.query.toLowerCase().includes(query)) &&
      (!status || report.status === status),
    );
    return { items, next_cursor: null } satisfies ReportListResponse as T;
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    if (path !== "/v1/reports") throw new Error("This demo action is not available.");
    const request = body as CreateReportRequest;
    const now = new Date().toISOString();
    const report: ReportSummary = {
      report_id: `demo-${Date.now()}`,
      title: request.title,
      status: "DRAFT",
      current_version: null,
      updated_at: now,
      subject: request.subject,
      focus: request.focus,
      depth: request.depth,
    };
    demoReports = [report, ...demoReports];
    return report as T;
  },

  async delete<T>(path: string): Promise<T> {
    const id = decodeURIComponent(path.split("/").pop() ?? "");
    demoReports = demoReports.filter((report) => report.report_id !== id);
    return undefined as T;
  },
};

