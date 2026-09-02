"""Shared immutable contracts for deterministic, explainable score engines.

Scores are projections of the truth ledger.  These models deliberately retain
methodology, inputs, coverage, and a machine-readable breakdown so a score can
be reproduced without treating it as an assertion of truth by itself.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScoreStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    NOT_ENOUGH_DATA = "NOT_ENOUGH_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConflictCap(StrEnum):
    NONE = "NONE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ScoreDimension(BaseModel):
    """One weighted dimension, including why it was or was not included."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(min_length=1)
    weight: float = Field(ge=0)
    value: float | None = Field(default=None, ge=0, le=1)
    normalized_weight: float = Field(default=0, ge=0, le=1)
    contribution: float = Field(default=0, ge=0, le=100)
    status: str = "INCLUDED"
    explanation: str = Field(min_length=1)


class ScoreResult(BaseModel):
    """Common response contract used by every score family."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    score: float | None = Field(default=None, ge=0, le=100)
    status: ScoreStatus
    method: str = Field(min_length=1)
    score_version: str = Field(min_length=1)
    coverage: float = Field(ge=0, le=100)
    coverage_factor: float = Field(ge=0, le=1)
    breakdown: dict[str, Any] = Field(default_factory=dict)
    input_ids: tuple[str, ...] = ()
    config_hash: str = Field(min_length=64, max_length=64)
    explanation: str = Field(min_length=1)

    @property
    def value(self) -> float | None:
        """Compatibility alias for clients that call scores ``value``."""

        return self.score

    @property
    def confidence_score(self) -> float | None:
        return self.score

    @property
    def drilldown(self) -> dict[str, Any]:
        return self.breakdown

    @property
    def version(self) -> str:
        return self.score_version

    @property
    def state(self) -> str:
        """Compatibility label for API/fixture consumers."""
        explicit = self.breakdown.get("state")
        if isinstance(explicit, str):
            return explicit
        return "SCORED" if self.status is ScoreStatus.AVAILABLE else self.status.value

    @property
    def sample_size(self) -> int:
        return int(
            self.breakdown.get("total_self_reported_claims", self.breakdown.get("claims", 0)) or 0
        )

    @property
    def label(self) -> str:
        return str(self.breakdown.get("label", self.method))

    @property
    def badges(self) -> list[str]:
        badges = self.breakdown.get("badges", [])
        return list(badges) if isinstance(badges, (list, tuple)) else []

    @property
    def cohort(self) -> str | None:
        value = self.breakdown.get("cohort")
        return value if isinstance(value, str) else None


class ClaimAssessment(BaseModel):
    """Minimal ledger projection consumed by report-level scoring."""

    model_config = ConfigDict(extra="allow", frozen=True)

    claim_id: str | None = None
    claim_version_id: str | None = None
    materiality: str = "MEDIUM"
    confidence: float | None = Field(default=None, ge=0, le=100)
    verdict: str = "UNVERIFIED"
    has_evidence: bool = False
    has_independent_evidence: bool = False
    freshness: str = "CURRENT"

    @property
    def input_id(self) -> str | None:
        return self.claim_version_id or self.claim_id


def materiality_weight(value: str | None) -> float:
    weights = {"LOW": 1.0, "MEDIUM": 2.0, "HIGH": 4.0, "CRITICAL": 8.0}
    return weights.get(str(value or "MEDIUM").upper(), 2.0)


__all__ = [
    "ClaimAssessment",
    "ConflictCap",
    "ScoreDimension",
    "ScoreResult",
    "ScoreStatus",
    "materiality_weight",
]
