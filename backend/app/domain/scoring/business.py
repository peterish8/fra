"""Cohort-aware deterministic financial/business score."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._common import number, result
from .models import ScoreResult, ScoreStatus

BUSINESS_VERSION = "financial-business-v1"


def score_business(
    *,
    cohort: str,
    stage: str | None,
    financials: Mapping[str, Any],
    score_version: str = BUSINESS_VERSION,
) -> ScoreResult:
    cohort_name = str(cohort or "UNKNOWN").upper()
    fields = {
        "PUBLIC": (
            ("revenue_growth", 0.3),
            ("margin", 0.25),
            ("cash_flow", 0.25),
            ("evidence_quality", 0.2),
        ),
        "PRIVATE": (
            ("revenue_growth", 0.25),
            ("traction", 0.3),
            ("funding", 0.25),
            ("evidence_quality", 0.2),
        ),
        "STARTUP": (
            ("traction", 0.35),
            ("funding", 0.25),
            ("revenue_growth", 0.2),
            ("evidence_quality", 0.2),
        ),
    }.get(cohort_name, (("evidence_quality", 1.0),))
    values: dict[str, float | None] = {}
    for key, _weight in fields:
        raw = financials.get(key)
        val = number(raw)
        if key == "revenue_growth" and val is not None and val > 1:
            base = number(financials.get("revenue_base")) or 0
            val = min(1.0, val / 10.0) if base >= 10000 else min(1.0, val / 20.0)
        values[key] = val
    applicable = [(key, weight, values[key]) for key, weight in fields if values[key] is not None]
    total = sum(weight for _, weight, _ in applicable)
    score = sum(value * weight for _, weight, value in applicable) / total * 100 if total else None
    coverage = total * 100
    status = ScoreStatus.AVAILABLE if score is not None else ScoreStatus.NOT_ENOUGH_DATA
    breakdown = {
        "cohort": cohort_name,
        "stage": stage,
        "components": {key: values[key] for key, _ in fields},
        "cohort_components": [key for key, _ in fields],
        "coverage_weight": coverage,
    }
    breakdown[f"{cohort_name.lower()}_model"] = True
    if score is None:
        breakdown["state"] = "COVERAGE_LIMITATION"
    return result(
        score=score,
        status=status,
        method="cohort-normalized-components",
        score_version=score_version,
        coverage=coverage,
        breakdown=breakdown,
        config={"cohort": cohort_name, "stage": stage, "weights": dict(fields)},
        explanation=(
            "Financial/business components are normalized within an explicit cohort; "
            "missing data remains unknown."
        ),
    )


calculate_business_score = score_business

__all__ = ["BUSINESS_VERSION", "score_business", "calculate_business_score"]
