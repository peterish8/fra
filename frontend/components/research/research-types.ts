export type ResearchDepth = "FAST" | "STANDARD" | "DEEP";
export type ResearchMode = "INITIATION" | "UPDATE" | "EARNINGS" | "EVENT" | "SECTOR" | "DILIGENCE";

export type ReportStatus = "DRAFT" | "RESEARCHING" | "READY" | "VERIFIED" | string;

export type ReportSubject = {
  query: string;
  country_code?: string;
  ticker?: string;
  domain?: string;
};

export type CreateReportRequest = {
  title: string;
  subject: ReportSubject;
  focus: string[];
  depth: ResearchDepth;
  research_mode: ResearchMode;
};

export type ReportSummary = {
  report_id: string;
  title: string;
  status: ReportStatus;
  current_version: number | null;
  updated_at: string;
  subject?: ReportSubject;
  focus?: string[];
  depth?: ResearchDepth;
  research_mode?: ResearchMode;
};

export type ReportDetail = ReportSummary & {
  company?: Record<string, unknown>;
  quality?: Record<string, unknown>;
};

export type ReportListResponse = {
  items: ReportSummary[];
  next_cursor: string | null;
};

export type ReportApiClient = {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown, options?: { headers?: HeadersInit }): Promise<T>;
  delete<T>(path: string, options?: { headers?: HeadersInit }): Promise<T>;
};

export const FOCUS_OPTIONS = [
  { value: "financials", label: "Financials", description: "Reported performance and metrics" },
  { value: "growth", label: "Growth", description: "Traction, scale, and momentum" },
  { value: "risks", label: "Risks", description: "Known risks and open questions" },
  { value: "recent_developments", label: "Recent developments", description: "Current events and changes" },
  { value: "competition", label: "Competition", description: "Market context and peers" },
  { value: "disclosure", label: "Disclosure verification", description: "What the company says" },
  { value: "full_research", label: "Full research", description: "All available research sections" },
] as const;

export const DEPTH_OPTIONS: Array<{ value: ResearchDepth; label: string; description: string }> = [
  { value: "FAST", label: "Fast", description: "A focused first pass" },
  { value: "STANDARD", label: "Standard", description: "Balanced coverage for most workspaces" },
  { value: "DEEP", label: "Deep", description: "Broader, more deliberate verification" },
];

export const RESEARCH_MODE_OPTIONS: Array<{ value: ResearchMode; label: string; description: string }> = [
  { value: "INITIATION", label: "Initiation", description: "Build the first evidence-backed company view" },
  { value: "UPDATE", label: "Update", description: "Revisit what changed since the prior version" },
  { value: "EARNINGS", label: "Earnings", description: "Read results, guidance, and open questions" },
  { value: "EVENT", label: "Event", description: "Assess a filing, rating action, or material event" },
  { value: "SECTOR", label: "Sector", description: "Compare shared drivers across a peer set" },
  { value: "DILIGENCE", label: "Diligence", description: "Investigate disclosure, identity, and risk evidence" },
];

export const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "DRAFT", label: "Draft" },
  { value: "RESEARCHING", label: "Researching" },
  { value: "READY", label: "Ready" },
  { value: "VERIFIED", label: "Verified" },
] as const;

export function formatReportDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function statusLabel(status: ReportStatus): string {
  return status
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim()) return error.message;
  if (typeof error === "object" && error !== null && "message" in error) {
    const message = error.message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}
