import { ComparisonTable } from "@/components/comparison/comparison-table";
export default function ComparePage() { return <main><ComparisonTable companies={["Company A", "Company B"]} metrics={[{ metric: "Revenue growth", compatible: true, values: [{ company_id: "a", value: "Unknown" }, { company_id: "b", value: "Unknown" }], warning: "UNKNOWN_OR_MISSING" }]} /></main>; }
