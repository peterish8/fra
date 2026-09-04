export type QuotaStatus = "AVAILABLE" | "NEARING_LIMIT" | "AT_LIMIT";

export type AdminUserUsage = {
  user_id: string;
  display_name: string;
  role: "USER" | "ADMIN";
  research_runs_used: number;
  research_runs_limit: number;
  quota_status: QuotaStatus;
};

export type AdminUsageOverview = {
  data_mode: "FIXTURE" | "LIVE";
  generated_at: string;
  observation_window_hours: number;
  registered_users: number;
  active_users_in_window: number;
  research_runs_in_window: number;
  users: AdminUserUsage[];
};

export const demoAdminUsageOverview: AdminUsageOverview = {
  data_mode: "FIXTURE",
  generated_at: "2026-09-04T10:30:00Z",
  observation_window_hours: 24,
  registered_users: 3,
  active_users_in_window: 3,
  research_runs_in_window: 22,
  users: [
    { user_id: "local-admin", display_name: "Local administrator", role: "ADMIN", research_runs_used: 4, research_runs_limit: 25, quota_status: "AVAILABLE" },
    { user_id: "local-analyst", display_name: "Local research analyst", role: "USER", research_runs_used: 8, research_runs_limit: 12, quota_status: "NEARING_LIMIT" },
    { user_id: "fixture-reviewer", display_name: "Fixture review account", role: "USER", research_runs_used: 10, research_runs_limit: 10, quota_status: "AT_LIMIT" },
  ],
};

export function quotaPercentage(user: AdminUserUsage): number {
  return Math.min(100, Math.round((user.research_runs_used / user.research_runs_limit) * 100));
}
