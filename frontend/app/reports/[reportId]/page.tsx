import Link from "next/link";
import { notFound } from "next/navigation";

import { ReportReader } from "@/components/report/report-reader";
import { demoClaims } from "@/lib/demo-data";
import { getDemoReportSummary } from "@/lib/demo-api-client";

type ReportDetailPageProps = {
  params: Promise<{ reportId: string }>;
};

export default async function ReportDetailPage({ params }: ReportDetailPageProps) {
  const { reportId } = await params;
  const report = getDemoReportSummary(reportId);
  if (!report) notFound();

  return (
    <div className="report-route">
      <nav className="report-route-nav" aria-label="Report location">
        <Link href="/reports">Reports</Link>
        <span aria-hidden="true">/</span>
        <span>{report.title}</span>
        <Link className="report-route-history" href={`/reports/${encodeURIComponent(report.report_id)}/history`}>
          Version history
        </Link>
      </nav>
      <ReportReader claims={demoClaims} title={report.title} />
    </div>
  );
}
