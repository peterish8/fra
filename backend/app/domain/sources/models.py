"""Provider-neutral source ledger records and retention contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .identity import canonical_document_identity


class SourceOwnership(StrEnum):
    """How a source relates to the researched company."""

    SELF_REPORTED = "SELF_REPORTED"
    INDEPENDENT = "INDEPENDENT"
    GOVERNMENT = "GOVERNMENT"
    REGULATOR = "REGULATOR"
    FILING = "FILING"
    STRUCTURED_PROVIDER = "STRUCTURED_PROVIDER"
    UNKNOWN = "UNKNOWN"
    UNCONFIRMED = "UNCONFIRMED"


class AuthorityTier(StrEnum):
    """Contextual authority tiers from the verification specification."""

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    D1 = "D1"
    E1 = "E1"
    E2 = "E2"


class RetentionMode(StrEnum):
    """What content may be retained under source/provider terms."""

    METADATA_ONLY = "METADATA_ONLY"
    EXCERPT_ONLY = "EXCERPT_ONLY"
    FULL_TEXT = "FULL_TEXT"
    STORAGE_REFERENCE = "STORAGE_REFERENCE"


class SourceRelationshipType(StrEnum):
    """Relationships used to collapse fake consensus without losing URLs."""

    DUPLICATE_OF = "DUPLICATE_OF"
    SYNDICATED_FROM = "SYNDICATED_FROM"
    QUOTES = "QUOTES"
    DERIVED_FROM = "DERIVED_FROM"
    DERIVED_FROM_COMPANY_RELEASE = "DERIVED_FROM_COMPANY_RELEASE"
    SHARED_ROOT = "SHARED_ROOT"


class SourceRecord(BaseModel):
    """Stable source/document identity matching the ``sources`` table."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: UUID = Field(default_factory=uuid4)
    canonical_url: str | None = None
    external_document_id: str | None = None
    identity_key: str = ""
    publisher: str = Field(min_length=1, max_length=300)
    domain: str | None = Field(default=None, max_length=253)
    source_type: str = Field(min_length=1, max_length=80)
    authority_tier: AuthorityTier | str
    ownership_relation: SourceOwnership = SourceOwnership.UNKNOWN
    is_primary_source: bool = False
    language: str | None = Field(default=None, max_length=32)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("canonical_url", "domain", "external_document_id", "language")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def derive_identity_key(self) -> SourceRecord:
        derived = canonical_document_identity(
            canonical_url=self.canonical_url,
            external_document_id=self.external_document_id,
        )
        if self.identity_key and self.identity_key != derived:
            raise ValueError("identity_key must match the canonical source identity")
        object.__setattr__(self, "identity_key", derived)
        return self


class SourceSnapshotRecord(BaseModel):
    """Immutable point-in-time source content and provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    title: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = Field(min_length=64, max_length=64)
    extracted_text: str | None = None
    storage_ref: str | None = None
    retention_mode: RetentionMode = RetentionMode.METADATA_ONLY
    redirect_chain: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("retrieved_at", "published_at")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @field_validator("content_hash")
    @classmethod
    def normalize_hash(cls, value: str) -> str:
        normalized = value.strip().lower()
        if any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("content_hash must be a SHA-256 hexadecimal digest")
        return normalized

    @field_validator("redirect_chain")
    @classmethod
    def normalize_redirects(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(item.strip() for item in value if item.strip())


class SourceSnapshotInput(BaseModel):
    """Input for a snapshot that enforces retention-safe content handling."""

    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    title: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime | None = None
    content: str | bytes | None = None
    content_hash: str | None = None
    permitted_excerpt: str | None = None
    extracted_text: str | None = None
    storage_ref: str | None = None
    retention_mode: RetentionMode = RetentionMode.METADATA_ONLY
    redirect_chain: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("retrieved_at", "published_at")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @field_validator("permitted_excerpt", "extracted_text", "storage_ref", "title")
    @classmethod
    def trim_optional_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class SourceRelationshipRecord(BaseModel):
    """Directed provenance relationship between two source identities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relationship_id: UUID = Field(default_factory=uuid4)
    from_source_id: UUID
    to_source_id: UUID
    relationship_type: SourceRelationshipType | str
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1, max_length=1000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("from_source_id", "to_source_id")
    @classmethod
    def distinct_sources(cls, value: UUID, info: Any) -> UUID:
        # The cross-field self-edge check is performed in the ledger because
        # Pydantic field validation order is not part of this public contract.
        del info
        return value


class RunSourceLink(BaseModel):
    """Application representation of the ``run_sources`` join table."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    research_run_id: UUID
    snapshot_id: UUID
    discovered_by_provider_request_id: UUID | None = None
    purpose: str | None = None


__all__ = [
    "AuthorityTier",
    "RetentionMode",
    "RunSourceLink",
    "SourceOwnership",
    "SourceRecord",
    "SourceRelationshipRecord",
    "SourceRelationshipType",
    "SourceSnapshotInput",
    "SourceSnapshotRecord",
    "Source",
    "SourceSnapshot",
]

# Domain-friendly aliases; storage-facing names remain the canonical exports.
Source = SourceRecord
SourceSnapshot = SourceSnapshotRecord
