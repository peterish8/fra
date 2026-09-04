import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import * as React from "react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ClaimsTable } from "../../components/claims/claims-table";
import { EvidenceInspector } from "../../components/evidence/evidence-inspector";
import { ReportReader } from "../../components/report/report-reader";
import { WatchlistTable } from "../../components/watchlist/watchlist-table";

// The current app components use the classic JSX runtime. Keep this contract
// test independent of a production-runtime change by providing its JSX global.
(globalThis as Record<string, unknown>).React = React;

const routes = ["research", "discover", "compare", "reports"];

describe("critical browser-flow contracts", () => {
  it("keeps all release routes present", () => {
    for (const route of routes) {
      const page = route === "reports" ? "reports/page.tsx" : `${route}/page.tsx`;
      expect(() => readFileSync(resolve(__dirname, `../../app/${page}`), "utf8")).not.toThrow();
    }
    expect(() => readFileSync(resolve(__dirname, "../../app/reports/[reportId]/page.tsx"), "utf8")).not.toThrow();
    expect(() => readFileSync(resolve(__dirname, "../../app/reports/[reportId]/history/page.tsx"), "utf8")).not.toThrow();
    expect(() => readFileSync(resolve(__dirname, "../../app/reports/[reportId]/not-found.tsx"), "utf8")).not.toThrow();
    expect(() => readFileSync(resolve(__dirname, "../../app/global-error.tsx"), "utf8")).not.toThrow();
  });

  it("renders report, evidence, contradicted filter, and empty states with accessible affordances", () => {
    const claims = [{ id: "c1", text: "Revenue is contradicted", origin: "Independent" as const, materiality: "HIGH", verdict: "CONTRADICTED", confidence: 24, sourceFamily: "Filing" }];
    const report = renderToStaticMarkup(createElement(ReportReader, { claims }));
    const table = renderToStaticMarkup(createElement(ClaimsTable, { claims, onInspect: () => undefined }));
    const drawer = renderToStaticMarkup(createElement(EvidenceInspector, { claim: claims[0], onClose: () => undefined }));
    expect(report).toContain("Disclosure Reliability");
    expect(table).toContain("CONTRADICTED");
    expect(table).toMatch(/select|Filter/);
    expect(drawer).toMatch(/role="dialog"|aria-modal/);
    expect(drawer).toContain("Evidence inspector");
  });

  it("shows honest empty/partial watchlist states and non-advice language", () => {
    const empty = renderToStaticMarkup(createElement(WatchlistTable, { entries: [], status: "STAGING" }));
    expect(empty).toContain("not investment advice");
    expect(empty).toMatch(/not published|No candidates qualify/);
    expect(empty).toMatch(/role="status"/);
  });

  it("keeps status available to keyboard and non-color users", () => {
    const markup = renderToStaticMarkup(createElement(ClaimsTable, { claims: [], onInspect: () => undefined }));
    expect(markup).toMatch(/aria-labelledby|role="status"/);
    expect(markup).toContain("No claims match this filter");
  });

  it("escapes untrusted claim text instead of rendering executable HTML", () => {
    const claims = [{
      id: "xss-1",
      text: '<img src=x onerror="alert(1)">',
      origin: "Company" as const,
      materiality: "HIGH",
      verdict: "UNVERIFIED",
    }];
    const markup = renderToStaticMarkup(
      createElement(ClaimsTable, { claims, onInspect: () => undefined }),
    );
    expect(markup).not.toContain('<img src=x onerror="alert(1)">');
    expect(markup).toContain("&lt;img");
  });
});
