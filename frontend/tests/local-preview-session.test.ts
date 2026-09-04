import { describe, expect, it } from "vitest";

import { normalizeLocalPreviewRole, parseLocalPreviewSession } from "../lib/local-preview-session";

describe("localhost preview roles", () => {
  it("keeps the legacy boolean session least-privileged", () => {
    expect(parseLocalPreviewSession("true")).toEqual({ role: "researcher" });
  });

  it("accepts only the explicit local admin role", () => {
    expect(parseLocalPreviewSession('{"role":"admin"}')).toEqual({ role: "admin" });
    expect(parseLocalPreviewSession('{"role":"owner"}')).toEqual({ role: "researcher" });
    expect(normalizeLocalPreviewRole("administrator")).toBe("researcher");
  });

  it("treats malformed storage as signed out", () => {
    expect(parseLocalPreviewSession("not-json")).toBeNull();
  });
});
