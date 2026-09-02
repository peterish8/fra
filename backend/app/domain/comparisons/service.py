from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def compare_companies(
    companies: Sequence[Mapping[str, Any]], metrics: Sequence[str] | None = None
) -> dict[str, Any]:
    if len(companies) < 2:
        raise ValueError("at least two companies are required")
    keys = list(metrics or {key for company in companies for key in company.get("metrics", {})})
    warnings: list[str] = []
    cohorts = {str(company.get("cohort", "UNKNOWN")).upper() for company in companies}
    if len(cohorts) > 1:
        warnings.append("COHORT_INCOMPATIBLE: values are shown but not ranked together")
    rows = []
    for metric in keys:
        values = []
        for company in companies:
            raw = (
                company.get("metrics", {}).get(metric)
                if isinstance(company.get("metrics", {}), Mapping)
                else None
            )
            values.append(
                {
                    "company_id": str(company.get("company_id", "")),
                    "value": raw,
                    "claim_version_id": company.get("claim_version_ids", {}).get(metric)
                    if isinstance(company.get("claim_version_ids", {}), Mapping)
                    else None,
                }
            )
        rows.append(
            {
                "metric": metric,
                "values": values,
                "compatible": not (len(cohorts) > 1),
                "warning": "UNKNOWN_OR_MISSING"
                if any(item["value"] is None for item in values)
                else None,
            }
        )
    return {
        "companies": [str(company.get("company_id", "")) for company in companies],
        "cohort": ",".join(sorted(cohorts)),
        "metrics": rows,
        "warnings": warnings,
    }
