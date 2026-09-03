import { describe, expect, it } from "vitest";

import { applyResearchHandoff, type FormValues } from "../components/research/research-form";

const draft: FormValues = {
  title: "Existing analyst title",
  query: "",
  countryCode: "US",
  ticker: "",
  domain: "",
  focus: ["financials"],
  depth: "STANDARD",
  researchMode: "INITIATION",
};

describe("research form URL handoff", () => {
  it("updates the subject, ticker, and mode while preserving the rest of the draft", () => {
    expect(applyResearchHandoff(draft, " NVIDIA ", " nvda ", "EARNINGS")).toEqual({
      ...draft,
      query: "NVIDIA",
      ticker: "NVDA",
      researchMode: "EARNINGS",
    });
  });
});
