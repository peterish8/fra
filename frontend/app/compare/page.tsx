import { ComparisonTable } from "@/components/comparison/comparison-table";
import { demoComparisonMetrics } from "@/lib/demo-data";

export default function ComparePage() { return <main><ComparisonTable companies={["NVIDIA", "Shopify", "Adobe"]} metrics={demoComparisonMetrics} /></main>; }
