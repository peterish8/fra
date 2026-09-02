"""Deterministic claim-confidence scoring with explicit N/A re-normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ._common import as_mapping, first, number, result, weighted_dimensions
from .models import ConflictCap, ScoreResult, ScoreStatus

CLAIM_CONFIDENCE_VERSION = "claim-confidence-v1"
CLAIM_CONFIDENCE_METHOD = "weighted-evidence-dimensions"
DEFAULT_WEIGHTS: dict[str, float] = {
    "semantic": 30.0,
    "authority": 15.0,
    "independence": 15.0,
    "numeric": 10.0,
    "temporal": 10.0,
    "agreement": 10.0,
    "freshness": 5.0,
    "adversarial": 5.0,
}


class ClaimConfidenceInput(BaseModel):
    """Accepted ledger dimensions; values are fractions in the range 0..1."""

    model_config = ConfigDict(extra="allow", frozen=True)

    claim_id: str | None = None
    claim_version_id: str | None = None
    materiality: str = "MEDIUM"
    semantic: float | str | None = Field(default=None, ge=0, le=1)
    semantic_support: float | str | None = None
    semantic_evidence_support: float | str | None = None
    authority: float | str | None = None
    source_authority: float | str | None = None
    source_authority_context_fit: float | str | None = None
    independence: float | str | None = None
    independent_support: float | str | None = None
    independent_source_support: float | str | None = None
    numeric: float | str | None = None
    numeric_validation: float | str | None = None
    temporal: float | str | None = None
    temporal_validation: float | str | None = None
    agreement: float | str | None = None
    cross_source_agreement: float | str | None = None
    freshness: float | str | None = None
    adversarial: float | str | None = None
    adversarial_survival: float | str | None = None
    conflict_severity: str | ConflictCap | None = None
    unresolved_conflict_severity: str | ConflictCap | None = None
    input_ids: tuple[str, ...] = ()


def score_claim_confidence(
    value: ClaimConfidenceInput | Mapping[str, Any] | None = None,
    *,
    score_version: str = CLAIM_CONFIDENCE_VERSION,
    weights: Mapping[str, float] | None = None,
    dimensions: Mapping[str, Any] | None = None,
    conflict: str | None = None,
    freshness: str | float | None = None,
    identity_resolved: bool = True,
    materiality: str | None = None,
) -> ScoreResult:
    """Return a reproducible 0..100 explanatory score, never a verdict."""

    data = dict(as_mapping(value or {}))
    if dimensions is not None:
        data.update(dimensions)
    if conflict is not None:
        data["conflict_severity"] = conflict
    if freshness is not None:
        data["freshness"] = freshness
    if materiality is not None:
        data["materiality"] = materiality
    configured = dict(DEFAULT_WEIGHTS if weights is None else weights)
    dimension_inputs: list[tuple[str, float, float | None, str]] = [
        (
            "semantic",
            configured.get("semantic", 30),
            number(first(data, "semantic", "semantic_support", "semantic_evidence_support")),
            "Semantic overlap/support from supplied evidence.",
        ),
        (
            "authority",
            configured.get("authority", 15),
            number(first(data, "authority", "source_authority", "source_authority_context_fit")),
            "Authority is evaluated for this fact's context.",
        ),
        (
            "independence",
            configured.get("independence", 15),
            number(
                first(data, "independence", "independent_support", "independent_source_support")
            ),
            "Independent source-family support; repeated URLs do not add weight.",
        ),
        (
            "numeric",
            configured.get("numeric", 10),
            number(first(data, "numeric", "numeric_validation")),
            "Deterministic numeric validation.",
        ),
        (
            "temporal",
            configured.get("temporal", 10),
            number(first(data, "temporal", "temporal_validation")),
            "Period and temporal alignment validation.",
        ),
        (
            "agreement",
            configured.get("agreement", 10),
            number(first(data, "agreement", "cross_source_agreement")),
            "Agreement among comparable evidence.",
        ),
        (
            "freshness",
            configured.get("freshness", 5),
            number(first(data, "freshness")),
            "Evidence freshness state.",
        ),
        (
            "adversarial",
            configured.get("adversarial", 5),
            number(first(data, "adversarial", "adversarial_survival")),
            "Survival of configured adversarial follow-ups.",
        ),
    ]
    raw_score, dimension_records = weighted_dimensions(dimension_inputs)
    cap = _conflict_cap(first(data, "conflict_severity", "unresolved_conflict_severity"))
    capped_score = raw_score
    if capped_score is not None and cap is not ConflictCap.NONE:
        capped_score = min(capped_score, 49.0 if cap is ConflictCap.CRITICAL else 69.0)
    if capped_score is not None and not identity_resolved:
        capped_score = min(capped_score, 69.0)
    if capped_score is not None and str(first(data, "freshness", default="")).upper() == "STALE":
        capped_score = min(capped_score, 85.0)
    identifier = first(data, "claim_version_id", "claim_id")
    ids = tuple(str(item) for item in first(data, "input_ids", default=()) or ())
    if identifier and str(identifier) not in ids:
        ids = (str(identifier), *ids)
    breakdown = {
        "dimensions": [record.model_dump(mode="json") for record in dimension_records],
        **{
            record.key: {"state": record.status, "value": record.value}
            for record in dimension_records
        },
        "raw_score": raw_score,
        "conflict_cap": cap.value,
        "cap_applied": raw_score is not None and capped_score != raw_score,
        "threshold_for_verified": 85.0,
        "verdict_note": (
            "This score explains evidence quality; rule gates determine the claim verdict."
        ),
    }
    status = ScoreStatus.AVAILABLE if raw_score is not None else ScoreStatus.NOT_ENOUGH_DATA
    explanation = "Weighted evidence dimensions were re-normalized over applicable inputs."
    if cap is not ConflictCap.NONE:
        explanation += f" An unresolved {cap.value} conflict caps confidence."
    if not identity_resolved:
        explanation += " Entity identity is unresolved, so confidence is capped."
    if raw_score is None:
        explanation = "No applicable evidence dimensions were supplied."
    return result(
        score=capped_score,
        status=status,
        method=CLAIM_CONFIDENCE_METHOD,
        score_version=score_version,
        coverage=100.0 if raw_score is not None else 0.0,
        breakdown=breakdown,
        input_ids=ids,
        config={
            "weights": configured,
            "verified_threshold": 85,
            "conflict_caps": {"HIGH": 69, "CRITICAL": 49},
        },
        explanation=explanation,
    )


def _conflict_cap(value: Any) -> ConflictCap:
    normalized = str(value or "NONE").upper()
    if "CRITICAL" in normalized:
        return ConflictCap.CRITICAL
    if "HIGH" in normalized:
        return ConflictCap.HIGH
    return ConflictCap.NONE


compute_claim_confidence = score_claim_confidence
calculate_claim_confidence = score_claim_confidence


class ClaimConfidenceEngine:
    def __init__(
        self,
        *,
        score_version: str = CLAIM_CONFIDENCE_VERSION,
        weights: Mapping[str, float] | None = None,
    ) -> None:
        self.score_version = score_version
        self.weights = weights

    def score(self, value: ClaimConfidenceInput | Mapping[str, Any]) -> ScoreResult:
        return score_claim_confidence(value, score_version=self.score_version, weights=self.weights)

    compute = score


__all__ = [
    "CLAIM_CONFIDENCE_METHOD",
    "CLAIM_CONFIDENCE_VERSION",
    "ClaimConfidenceEngine",
    "ClaimConfidenceInput",
    "calculate_claim_confidence",
    "compute_claim_confidence",
    "score_claim_confidence",
]
