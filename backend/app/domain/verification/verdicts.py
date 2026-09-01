"""Rule-first canonical claim verdict decisions."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.claims.models import ClaimFreshness, ClaimVerdict

from .semantic import SemanticOutcome


class VerdictInput(BaseModel):
    """Deterministic gates supplied by verification workers."""

    model_config = ConfigDict(extra="forbid")

    semantic_outcomes: list[SemanticOutcome] = Field(default_factory=list)
    has_evidence: bool = False
    has_independent_evidence: bool = False
    critical_conflict: bool = False
    identity_passed: bool = True
    numeric_passed: bool | None = None
    temporal_passed: bool | None = None
    freshness: ClaimFreshness = ClaimFreshness.CURRENT
    materiality: str = "MEDIUM"


class VerdictDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: ClaimVerdict
    reason: str = Field(min_length=1)
    blocking: bool


def determine_verdict(
    value: VerdictInput | None = None, **legacy: Any
) -> VerdictDecision:
    """Apply canonical outcomes before any numerical confidence score."""

    if value is None:
        value = _legacy_verdict_input(legacy)

    if value.freshness in {ClaimFreshness.STALE, ClaimFreshness.INVALIDATED}:
        return VerdictDecision(
            verdict=ClaimVerdict.STALE,
            reason="Existing evidence no longer meets the configured freshness state.",
            blocking=True,
        )
    if not value.has_evidence:
        return VerdictDecision(
            verdict=ClaimVerdict.INSUFFICIENT_EVIDENCE,
            reason="No evidence relation is available for this claim.",
            blocking=True,
        )
    if SemanticOutcome.FAIL in value.semantic_outcomes and value.has_independent_evidence:
        return VerdictDecision(
            verdict=ClaimVerdict.CONTRADICTED,
            reason="Independent supplied evidence directly contradicts the claim.",
            blocking=True,
        )
    if value.critical_conflict:
        return VerdictDecision(
            verdict=ClaimVerdict.PARTIALLY_SUPPORTED,
            reason="A material conflict remains unresolved; the claim cannot be verified.",
            blocking=True,
        )
    if SemanticOutcome.PARTIAL in value.semantic_outcomes:
        return VerdictDecision(
            verdict=ClaimVerdict.PARTIALLY_SUPPORTED,
            reason="Only part of the claim is supported by supplied evidence.",
            blocking=True,
        )
    if not value.identity_passed or value.numeric_passed is False or value.temporal_passed is False:
        return VerdictDecision(
            verdict=ClaimVerdict.UNVERIFIED,
            reason="A required identity, numeric, or temporal gate did not pass.",
            blocking=True,
        )
    if SemanticOutcome.PASS not in value.semantic_outcomes:
        return VerdictDecision(
            verdict=ClaimVerdict.UNVERIFIED,
            reason="Supplied evidence does not establish the claim.",
            blocking=True,
        )
    if not value.has_independent_evidence and value.materiality.upper() != "LOW":
        return VerdictDecision(
            verdict=ClaimVerdict.UNVERIFIED,
            reason="Independent evidence is required for this material claim.",
            blocking=True,
        )
    return VerdictDecision(
        verdict=ClaimVerdict.VERIFIED,
        reason="Supplied evidence and required deterministic gates passed.",
        blocking=False,
    )


def _legacy_verdict_input(values: dict[str, Any]) -> VerdictInput:
    """Accept the fixture/API draft vocabulary while keeping one rule engine."""

    outcome = str(values.get("verification_outcome", "INSUFFICIENT")).upper()
    try:
        semantic = [SemanticOutcome(outcome)]
    except ValueError:
        semantic = [SemanticOutcome.INSUFFICIENT]
    numeric = values.get("numeric_check")
    temporal = values.get("temporal_check")
    return VerdictInput(
        semantic_outcomes=semantic,
        has_evidence=outcome != SemanticOutcome.INSUFFICIENT.value
        and float(values.get("citation_coverage", 0)) > 0,
        has_independent_evidence=bool(values.get("independent_evidence", False)),
        critical_conflict=bool(values.get("critical_conflict", False)),
        identity_passed=bool(values.get("identity_complete", True)),
        numeric_passed=None if numeric in (None, "NOT_APPLICABLE") else str(numeric).upper() == "PASS",
        temporal_passed=None if temporal in (None, "NOT_APPLICABLE") else str(temporal).upper() == "PASS",
        freshness=ClaimFreshness(str(values.get("freshness", ClaimFreshness.CURRENT)).upper()),
    )


__all__ = ["VerdictDecision", "VerdictInput", "determine_verdict"]
