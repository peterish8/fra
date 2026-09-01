"""Atomic claim, version, and evidence relation records."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClaimOrigin(StrEnum):
    SELF_REPORTED = "SELF_REPORTED"
    INDEPENDENT = "INDEPENDENT"
    DERIVED = "DERIVED"
    SYSTEM = "SYSTEM"


class ClaimVerdict(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    STALE = "STALE"


class ClaimFreshness(StrEnum):
    CURRENT = "CURRENT"
    AGING = "AGING"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class EvidenceRole(StrEnum):
    ORIGIN = "ORIGIN"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONTEXT = "CONTEXT"


class ClaimRecord(BaseModel):
    """Stable claim identity; changing wording belongs in versions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: UUID = Field(default_factory=uuid4)
    company_id: UUID | None = None
    canonical_key: str = Field(min_length=1, max_length=500)
    category: str = Field(min_length=1, max_length=120)
    origin: ClaimOrigin
    materiality: str = Field(default="MEDIUM", min_length=1, max_length=20)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClaimVersionRecord(BaseModel):
    """Append-only proposition version used by report views."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_version_id: UUID = Field(default_factory=uuid4)
    claim_id: UUID
    research_run_id: UUID | None = None
    statement: str = Field(min_length=1, max_length=4_000)
    structured_value: dict[str, Any] = Field(default_factory=dict)
    verdict: ClaimVerdict = ClaimVerdict.UNVERIFIED
    freshness: ClaimFreshness = ClaimFreshness.CURRENT
    supersedes_claim_version_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("statement")
    @classmethod
    def trim_statement(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("claim statement must not be blank")
        return normalized


class EvidenceRelationRecord(BaseModel):
    """Traceable link from a claim version to one source snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: UUID = Field(default_factory=uuid4)
    claim_version_id: UUID
    source_snapshot_id: UUID
    evidence_role: EvidenceRole
    excerpt: str | None = Field(default=None, max_length=20_000)
    locator: dict[str, Any] = Field(default_factory=dict)
    is_independent: bool
    directness: float | None = Field(default=None, ge=0, le=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("excerpt")
    @classmethod
    def normalize_excerpt(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ClaimInput(BaseModel):
    """Validated request for stable claim/version construction."""

    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1, max_length=4_000)
    category: str = Field(min_length=1, max_length=120)
    origin: ClaimOrigin
    materiality: str = Field(default="MEDIUM", min_length=1, max_length=20)
    company_id: UUID | None = None
    research_run_id: UUID | None = None
    canonical_key: str | None = Field(default=None, max_length=500)
    structured_value: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "ClaimFreshness",
    "ClaimInput",
    "ClaimOrigin",
    "ClaimRecord",
    "ClaimVerdict",
    "ClaimVersionRecord",
    "EvidenceRelationRecord",
    "EvidenceRole",
]
