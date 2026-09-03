"use client";

import ResearchWorkspace from "./research-workspace";
import { demoReportApiClient } from "@/lib/demo-api-client";

export function DemoResearchPage() {
  return <ResearchWorkspace apiClient={demoReportApiClient} />;
}

