"""Evidence-first analyst workflow contracts.

These objects are deliberately separate from claims and report versions: a
thesis point captures the researcher's question and falsifier, while the
Truth Ledger remains the canonical source for any factual verdict.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ThesisStatus(StrEnum):
    OPEN = "OPEN"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    UNCHANGED = "UNCHANGED"


class ChangeBriefKind(StrEnum):
    EARNINGS = "EARNINGS"
    FILING = "FILING"


class ChangeDirection(StrEnum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    WEAKENED = "WEAKENED"
    NEW_RISK = "NEW_RISK"
    UNCHANGED = "UNCHANGED"


class EvidenceCitation(BaseModel):
    """A retention-safe citation required for analyst-facing projections."""

    model_config = ConfigDict(extra="forbid")

    source_snapshot_id: UUID
    source_label: str = Field(min_length=1, max_length=180)
    excerpt: str = Field(min_length=1, max_length=600)
    retrieved_at: datetime


class ThesisPointCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=8, max_length=2000)
    falsifier: str = Field(min_length=8, max_length=2000)
    materiality: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")

    @field_validator("statement", "falsifier")
    @classmethod
    def trim_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class ThesisPointUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ThesisStatus
    review_note: str | None = Field(default=None, max_length=2000)
    linked_claim_version_ids: list[UUID] = Field(default_factory=list, max_length=32)

    @field_validator("review_note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ThesisPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thesis_point_id: UUID = Field(default_factory=uuid4)
    report_id: UUID
    statement: str
    falsifier: str
    materiality: str
    status: ThesisStatus = ThesisStatus.OPEN
    review_note: str | None = None
    linked_claim_version_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChangeBriefItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: ChangeDirection
    headline: str = Field(min_length=1, max_length=240)
    why_it_matters: str = Field(min_length=1, max_length=600)
    claim_version_id: UUID | None = None
    citations: list[EvidenceCitation] = Field(min_length=1, max_length=8)


class ChangeBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: UUID
    kind: ChangeBriefKind
    title: str
    as_of: datetime
    limitations: list[str] = Field(default_factory=list)
    items: list[ChangeBriefItem] = Field(default_factory=list)


class TearsheetSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    summary: str
    citations: list[EvidenceCitation] = Field(min_length=1, max_length=8)


class Tearsheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: UUID
    title: str
    as_of: datetime
    research_mode: str
    sections: list[TearsheetSection] = Field(min_length=1, max_length=8)
    open_questions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


__all__ = [
    "ChangeBrief",
    "ChangeBriefItem",
    "ChangeBriefKind",
    "ChangeDirection",
    "EvidenceCitation",
    "Tearsheet",
    "TearsheetSection",
    "ThesisPoint",
    "ThesisPointCreate",
    "ThesisPointUpdate",
    "ThesisStatus",
]
