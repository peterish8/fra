"""Report-level research-confidence score with coverage and gate factors."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

from ._common import result
from .coverage import calculate_evidence_coverage
from .models import ClaimAssessment, ScoreResult, ScoreStatus, materiality_weight

RESEARCH_CONFIDENCE_VERSION = "research-confidence-v1"


def score_research_confidence(
    claims: Iterable[ClaimAssessment | Mapping[str, Any]],
    *,
    coverage: float | ScoreResult | None = None,
    source_diversity: float | None = None,
    unresolved_conflicts: int = 0,
    conflict_penalty: float | None = None,
    stale_evidence_penalty: float = 0.0,
    identity_resolved: bool = True,
    publication_gate_complete: bool = True,
    citation_coverage: float | None = None,
    score_version: str = RESEARCH_CONFIDENCE_VERSION,
) -> ScoreResult:
    raw_records = list(claims)
    records = []
    for item in raw_records:
        if isinstance(item, ClaimAssessment):
            records.append(item)
        else:
            mapping = dict(item)
            if "evidence_coverage" in mapping and "has_evidence" not in mapping:
                mapping["has_evidence"] = float(mapping["evidence_coverage"] or 0) > 0
            records.append(ClaimAssessment.model_validate(mapping))
    if citation_coverage is not None and coverage is None:
        coverage = max(
            0.0,
            min(100.0, citation_coverage * 100 if citation_coverage <= 1 else citation_coverage),
        )
    ids = tuple(str(record.input_id) for record in records if record.input_id)
    coverage_result = calculate_evidence_coverage(records) if coverage is None else coverage
    coverage_pct = (
        coverage_result.score if isinstance(coverage_result, ScoreResult) else float(coverage or 0)
    )
    quality_denominator = sum(
        materiality_weight(record.materiality)
        for record in records
        if record.confidence is not None
    )
    quality = (
        sum(
            materiality_weight(record.materiality) * float(record.confidence or 0)
            for record in records
            if record.confidence is not None
        )
        / quality_denominator
        if quality_denominator
        else None
    )
    diversity = 1.0 if source_diversity is None else min(1.0, max(0.0, source_diversity))
    # The explicit gates are multiplicative factors, never hidden deductions.
    gate_factor = (1.0 if identity_resolved else 0.5) * (1.0 if publication_gate_complete else 0.75)
    penalty = float(
        conflict_penalty if conflict_penalty is not None else min(30.0, unresolved_conflicts * 8.0)
    )
    penalty += min(25.0, max(0.0, stale_evidence_penalty))
    raw_score = None
    if quality is not None:
        raw_score = (
            quality * math.sqrt(min(1.0, max(0.0, coverage_pct / 100))) * diversity * gate_factor
            - penalty
        )
        raw_score = max(0.0, raw_score)
    status = ScoreStatus.AVAILABLE if raw_score is not None else ScoreStatus.NOT_ENOUGH_DATA
    breakdown = {
        "weighted_claim_quality": quality,
        "evidence_coverage": coverage_pct,
        "source_diversity_factor": diversity,
        "identity_factor": 1.0 if identity_resolved else 0.5,
        "publication_gate_factor": 1.0 if publication_gate_complete else 0.75,
        "conflict_penalty": min(
            30.0,
            float(conflict_penalty if conflict_penalty is not None else unresolved_conflicts * 8.0),
        ),
        "stale_evidence_penalty": min(25.0, max(0.0, stale_evidence_penalty)),
        "claims": len(records),
        "coverage_breakdown": coverage_result.breakdown
        if isinstance(coverage_result, ScoreResult)
        else {},
    }
    explanation = (
        "Research confidence combines weighted claim quality, coverage, diversity, "
        "and explicit gates."
    )
    if not identity_resolved:
        explanation += " Entity identity is unresolved, so confidence is reduced."
    if raw_score is None:
        explanation = "No scored material claims are available for research confidence."
    return result(
        score=raw_score,
        status=status,
        method="quality-times-coverage-diversity-minus-penalties",
        score_version=score_version,
        coverage=coverage_pct,
        breakdown=breakdown,
        input_ids=ids,
        config={
            "formula": "quality * sqrt(coverage) * diversity * gates - penalties",
            "version": score_version,
        },
        explanation=explanation,
    )


compute_research_confidence = score_research_confidence
calculate_research_confidence = score_research_confidence


__all__ = [
    "RESEARCH_CONFIDENCE_VERSION",
    "calculate_research_confidence",
    "compute_research_confidence",
    "score_research_confidence",
]
