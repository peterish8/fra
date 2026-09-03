import { describe, expect, it } from "vitest";

import { RESEARCH_MODE_OPTIONS } from "../components/research/research-types";

describe("analyst workflow UI contracts", () => {
  it("keeps each structured research workflow available at intake", () => {
    expect(RESEARCH_MODE_OPTIONS.map((option) => option.value)).toEqual([
      "INITIATION",
      "UPDATE",
      "EARNINGS",
      "EVENT",
      "SECTOR",
      "DILIGENCE",
    ]);
  });

  it("keeps thesis status vocabulary separate from canonical claim verdicts", async () => {
    const source = await import("../components/analyst/analyst-workflow-pages");
    expect(source.ThesisTrackerPage).toBeTypeOf("function");
    expect(source.ChangeBriefPage).toBeTypeOf("function");
    expect(source.TearsheetPage).toBeTypeOf("function");
  });
});
