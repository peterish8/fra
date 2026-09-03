import { ReportReader } from "@/components/report/report-reader";
import { demoClaims } from "@/lib/demo-data";

export default function ReportsPage() {
  return <ReportReader claims={demoClaims} />;
}
