"""Materiality-weighted independent disclosure reliability scoring."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ._common import as_mapping, first, result
from .models import ScoreResult, ScoreStatus, materiality_weight

DISCLOSURE_VERSION = "disclosure-reliability-v1"
_OUTCOME_VALUES = {
    "VERIFIED": 1.0,
    "PARTIALLY_SUPPORTED": 0.6,
    "CONTRADICTED": 0.0,
}


def score_disclosure_reliability(
    claims: Iterable[Mapping[str, Any] | Any],
    *,
    min_claims: int = 5,
    min_coverage: float = 40.0,
    score_version: str = DISCLOSURE_VERSION,
) -> ScoreResult:
    records = [as_mapping(item) for item in claims]
    self_reported = [
        record
        for record in records
        if str(first(record, "origin", "claim_origin", default="SELF_REPORTED")).upper()
        == "SELF_REPORTED"
    ]
    total_weight = sum(
        materiality_weight(str(first(item, "materiality", default="MEDIUM")))
        for item in self_reported
    )
    assessed = [item for item in self_reported if _independently_assessed(item)]
    assessed_weight = sum(
        materiality_weight(str(first(item, "materiality", default="MEDIUM"))) for item in assessed
    )
    coverage = 100 * assessed_weight / total_weight if total_weight else 0.0
    denominator = sum(
        materiality_weight(str(first(item, "materiality", default="MEDIUM")))
        for item in assessed
        if str(first(item, "verdict", "outcome", default="UNVERIFIED")).upper() in _OUTCOME_VALUES
    )
    numerator = sum(
        materiality_weight(str(first(item, "materiality", default="MEDIUM")))
        * _OUTCOME_VALUES[str(first(item, "verdict", "outcome", default="UNVERIFIED")).upper()]
        for item in assessed
        if str(first(item, "verdict", "outcome", default="UNVERIFIED")).upper() in _OUTCOME_VALUES
    )
    score = 100 * numerator / denominator if denominator else None
    critical_contradiction = any(
        str(first(item, "materiality", default="MEDIUM")).upper() == "CRITICAL"
        and str(first(item, "verdict", "outcome", default="UNVERIFIED")).upper() == "CONTRADICTED"
        for item in self_reported
    )
    status = ScoreStatus.NOT_ENOUGH_DATA if not self_reported else ScoreStatus.AVAILABLE
    if self_reported and (
        len(assessed) < min_claims or coverage < min_coverage or denominator == 0
    ):
        status = ScoreStatus.NOT_ENOUGH_DATA
        score = None
    ids = tuple(
        str(first(item, "claim_version_id", "claim_id", "id"))
        for item in self_reported
        if first(item, "claim_version_id", "claim_id", "id") is not None
    )
    breakdown: dict[str, Any] = {
        "total_self_reported_claims": len(self_reported),
        "assessed_claims": len(assessed),
        "total_materiality_weight": total_weight,
        "assessed_materiality_weight": assessed_weight,
        "verified_weight": sum(
            materiality_weight(str(first(item, "materiality", default="MEDIUM")))
            for item in assessed
            if str(first(item, "verdict", "outcome", default="")).upper() == "VERIFIED"
        ),
        "partially_supported_weight": sum(
            materiality_weight(str(first(item, "materiality", default="MEDIUM")))
            for item in assessed
            if str(first(item, "verdict", "outcome", default="")).upper() == "PARTIALLY_SUPPORTED"
        ),
        "contradicted_weight": sum(
            materiality_weight(str(first(item, "materiality", default="MEDIUM")))
            for item in assessed
            if str(first(item, "verdict", "outcome", default="")).upper() == "CONTRADICTED"
        ),
        "coverage_gate": min_coverage,
        "sample_gate": min_claims,
        "material_contradiction": critical_contradiction,
    }
    badges = ["CRITICAL_CONTRADICTION"] if critical_contradiction else []
    breakdown["badges"] = badges
    breakdown["label"] = "Disclosure Reliability"
    return result(
        score=score,
        status=status,
        method="materiality-weighted-independent-disclosure-outcomes",
        score_version=score_version,
        coverage=coverage,
        breakdown=breakdown,
        input_ids=ids,
        config={
            "outcome_values": _OUTCOME_VALUES,
            "minimum_claims": min_claims,
            "minimum_coverage": min_coverage,
        },
        explanation=(
            "Disclosure Reliability measures independently assessable self-reported claims, "
            "not company trustworthiness."
            if self_reported
            else "No self-reported claims are available; more evidence is needed."
        ),
    )


def _independently_assessed(item: Mapping[str, Any]) -> bool:
    verdict = str(first(item, "verdict", "outcome", default="UNVERIFIED")).upper()
    return bool(
        first(
            item,
            "has_independent_evidence",
            "independent_evidence",
            "independently_assessed",
            default=True,
        )
    ) and verdict not in {"UNVERIFIED", "INSUFFICIENT_EVIDENCE"}


compute_disclosure_reliability = score_disclosure_reliability
calculate_disclosure_reliability = score_disclosure_reliability


__all__ = [
    "DISCLOSURE_VERSION",
    "calculate_disclosure_reliability",
    "compute_disclosure_reliability",
    "score_disclosure_reliability",
]
