"""Evidence coverage calculations used independently from confidence."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ._common import result
from .models import ClaimAssessment, ScoreResult, ScoreStatus, materiality_weight

COVERAGE_VERSION = "evidence-coverage-v1"


def calculate_evidence_coverage(
    claims: Iterable[ClaimAssessment | Mapping[str, Any]],
    *,
    score_version: str = COVERAGE_VERSION,
) -> ScoreResult:
    records = [
        ClaimAssessment.model_validate(item) if not isinstance(item, ClaimAssessment) else item
        for item in claims
    ]
    total = sum(materiality_weight(record.materiality) for record in records)
    assessed = sum(
        materiality_weight(record.materiality) for record in records if _assessed(record)
    )
    coverage = 100 * assessed / total if total else 0.0
    ids = tuple(str(record.input_id) for record in records if record.input_id)
    breakdown = {
        "total_materiality_weight": total,
        "assessed_materiality_weight": assessed,
        "unassessed_materiality_weight": max(0.0, total - assessed),
        "claims": len(records),
        "assessed_claims": sum(_assessed(record) for record in records),
        "input_ids": ids,
    }
    status = ScoreStatus.AVAILABLE if records and total else ScoreStatus.NOT_ENOUGH_DATA
    return result(
        score=coverage,
        status=status,
        method="materiality-weighted-evidence-coverage",
        score_version=score_version,
        coverage=coverage,
        breakdown=breakdown,
        input_ids=ids,
        config={"materiality_weights": {"LOW": 1, "MEDIUM": 2, "HIGH": 4, "CRITICAL": 8}},
        explanation=(
            "Coverage measures assessed materiality, not whether an assessed claim is true."
        ),
    )


def _assessed(record: ClaimAssessment) -> bool:
    verdict = record.verdict.upper()
    return bool(record.has_evidence or verdict not in {"UNVERIFIED", "INSUFFICIENT_EVIDENCE"})


compute_evidence_coverage = calculate_evidence_coverage
evidence_coverage = calculate_evidence_coverage


__all__ = [
    "COVERAGE_VERSION",
    "calculate_evidence_coverage",
    "compute_evidence_coverage",
    "evidence_coverage",
]
