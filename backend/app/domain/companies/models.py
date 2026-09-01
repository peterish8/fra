"""Typed contracts for conservative company identity resolution."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNCONFIRMED = "UNCONFIRMED"


class MatchReason(BaseModel):
    """A human-readable, machine-stable explanation for an identity signal."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=80)
    detail: str = Field(min_length=1, max_length=500)


class EntityQuery(BaseModel):
    """Identity hints supplied by a user or an upstream search adapter."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, max_length=250)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    domain: str | None = Field(default=None, max_length=253)
    ticker: str | None = Field(default=None, max_length=64)
    exchange: str | None = Field(default=None, max_length=64)
    registry: str | None = Field(default=None, max_length=100)
    registry_id: str | None = Field(default=None, max_length=200)
    lei: str | None = Field(default=None, max_length=64)

    @field_validator(
        "name", "country_code", "domain", "ticker", "exchange", "registry", "registry_id", "lei"
    )
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("ticker", "exchange", "registry")
    @classmethod
    def normalize_identifier_text(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class RegistryIdentifier(BaseModel):
    model_config = ConfigDict(extra="ignore")

    registry: str
    value: str


class CompanyAlias(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: str
    alias_type: str = "COMMON"
    valid_from: str | None = None
    valid_to: str | None = None


class CompanyCandidate(BaseModel):
    """Candidate identity plus resolver-produced explainability fields."""

    model_config = ConfigDict(extra="ignore")

    company_id: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1)
    entity_type: str = "OTHER"
    country_code: str | None = None
    primary_ticker: str | None = None
    primary_exchange: str | None = None
    domains: list[str] = Field(default_factory=list)
    aliases: list[CompanyAlias] = Field(default_factory=list)
    registry_identifiers: list[RegistryIdentifier] = Field(default_factory=list)
    confidence: float = 0.0
    match_reasons: list[MatchReason] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

    @classmethod
    def from_input(cls, value: dict[str, Any]) -> CompanyCandidate:
        """Parse fixture/storage naming variants without adding provider behavior."""

        payload = dict(value)
        if "canonical_name" not in payload and "name" in payload:
            payload["canonical_name"] = payload["name"]
        if "primary_ticker" not in payload and "ticker" in payload:
            payload["primary_ticker"] = payload["ticker"]
        if "primary_exchange" not in payload and "exchange" in payload:
            payload["primary_exchange"] = payload["exchange"]
        return cls.model_validate(payload)


class EntityResolution(BaseModel):
    """Deterministic resolution result; research may proceed only when resolved."""

    model_config = ConfigDict(extra="forbid")

    status: ResolutionStatus
    selected_company_id: str | None = None
    research_allowed: bool
    abstention_reason: str | None = None
    candidates: list[CompanyCandidate]
    match_reasons: list[MatchReason] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


__all__ = [
    "CompanyAlias",
    "CompanyCandidate",
    "EntityQuery",
    "EntityResolution",
    "MatchReason",
    "RegistryIdentifier",
    "ResolutionStatus",
]
