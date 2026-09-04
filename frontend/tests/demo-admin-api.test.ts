import { describe, expect, it } from "vitest";

import { demoAdminUsageOverview, quotaPercentage } from "../lib/demo-admin-api";

describe("local admin usage fixture", () => {
  it("labels fixture mode and exposes an explicit quota state for every account", () => {
    expect(demoAdminUsageOverview.data_mode).toBe("FIXTURE");
    expect(demoAdminUsageOverview.users).toHaveLength(demoAdminUsageOverview.registered_users);
    expect(demoAdminUsageOverview.users.map((user) => user.quota_status)).toEqual(["AVAILABLE", "NEARING_LIMIT", "AT_LIMIT"]);
  });

  it("caps rendered quota percentage at one hundred", () => {
    expect(quotaPercentage({ user_id: "test", display_name: "Test", role: "USER", research_runs_used: 14, research_runs_limit: 10, quota_status: "AT_LIMIT" })).toBe(100);
  });
});
