export type LocalPreviewRole = "researcher" | "admin";

export type StoredLocalPreviewSession = {
  role: LocalPreviewRole;
};

export function normalizeLocalPreviewRole(value: unknown): LocalPreviewRole {
  return value === "admin" ? "admin" : "researcher";
}

export function parseLocalPreviewSession(value: string | null): StoredLocalPreviewSession | null {
  if (value === null) return null;

  // Earlier localhost sessions stored just "true". Preserve that safe,
  // least-privileged session as a researcher rather than breaking preview.
  if (value === "true") return { role: "researcher" };

  try {
    const parsed: unknown = JSON.parse(value);
    if (typeof parsed === "object" && parsed !== null && "role" in parsed) {
      return { role: normalizeLocalPreviewRole(parsed.role) };
    }
  } catch {
    return null;
  }
  return null;
}
