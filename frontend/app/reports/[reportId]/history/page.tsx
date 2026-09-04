import Link from "next/link";
import { notFound } from "next/navigation";

import { VersionHistory } from "@/components/history/version-history";
import { getDemoReportSummary, getDemoReportVersions } from "@/lib/demo-api-client";

type ReportHistoryPageProps = {
  params: Promise<{ reportId: string }>;
};

export default async function ReportHistoryPage({ params }: ReportHistoryPageProps) {
  const { reportId } = await params;
  const report = getDemoReportSummary(reportId);
  if (!report) notFound();

  return (
    <main className="report-history-page">
      <header className="report-history-header">
        <p className="report-history-kicker">Living report</p>
        <h1>Report history</h1>
        <p>{report.title}</p>
        <Link href={`/reports/${encodeURIComponent(report.report_id)}`}>← Back to report</Link>
      </header>
      <VersionHistory versions={getDemoReportVersions(report.report_id)} />
    </main>
  );
}
