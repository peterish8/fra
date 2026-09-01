"""Typed report workspace DTOs and storage projections."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportDepth(StrEnum):
    FAST = "FAST"
    STANDARD = "STANDARD"
    DEEP = "DEEP"


class ReportStatus(StrEnum):
    DRAFT = "DRAFT"
    RESEARCHING = "RESEARCHING"
    READY = "READY"
    VERIFIED = "VERIFIED"
    ARCHIVED = "ARCHIVED"


class ReportSubject(BaseModel):
    """The user-provided subject used as the starting point for resolution."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=200)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    ticker: str | None = Field(default=None, min_length=1, max_length=32)
    domain: str | None = Field(default=None, min_length=1, max_length=253)

    @field_validator("query", "ticker", "domain")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None


class CreateReportRequest(BaseModel):
    """Validated request body for report workspace creation."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=180)
    subject: ReportSubject
    focus: list[str] = Field(default_factory=list, max_length=32)
    depth: ReportDepth = ReportDepth.STANDARD

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("focus")
    @classmethod
    def normalize_focus(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if not item:
                raise ValueError("focus values must not be blank")
            if len(item) > 64:
                raise ValueError("focus values must be 64 characters or fewer")
            normalized.append(item)
        return normalized


class ReportRecord(BaseModel):
    """Storage-facing report projection used by the domain service."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    report_id: UUID
    owner_user_id: str = Field(min_length=1)
    title: str
    subject: ReportSubject
    focus: list[str] = Field(default_factory=list)
    depth: ReportDepth
    status: ReportStatus = ReportStatus.DRAFT
    updated_at: datetime
    deleted_at: datetime | None = None
    current_version: int | None = None
    company_id: UUID | None = None

    @classmethod
    def from_storage(cls, value: Mapping[str, Any]) -> ReportRecord:
        """Parse the schema/fixture naming variants at the repository edge."""

        payload = dict(value)
        if "report_id" not in payload and "id" in payload:
            payload["report_id"] = payload["id"]
        if "company_id" not in payload and "primary_company_id" in payload:
            payload["company_id"] = payload["primary_company_id"]
        return cls.model_validate(payload)


class ReportSummary(BaseModel):
    """Compact report representation used by create and list endpoints."""

    report_id: UUID
    title: str
    status: ReportStatus
    current_version: int | None = None
    updated_at: datetime

    @classmethod
    def from_record(cls, record: ReportRecord) -> ReportSummary:
        return cls(
            report_id=record.report_id,
            title=record.title,
            status=record.status,
            current_version=record.current_version,
            updated_at=record.updated_at,
        )


class ReportDetail(ReportSummary):
    """Workspace metadata returned when a report is opened."""

    subject: ReportSubject
    focus: list[str]
    depth: ReportDepth
    company_id: UUID | None = None

    @classmethod
    def from_record(cls, record: ReportRecord) -> ReportDetail:
        return cls(
            **ReportSummary.from_record(record).model_dump(),
            subject=record.subject,
            focus=record.focus,
            depth=record.depth,
            company_id=record.company_id,
        )


class ReportListResponse(BaseModel):
    items: list[ReportSummary]
    next_cursor: str | None = None


__all__ = [
    "CreateReportRequest",
    "ReportDepth",
    "ReportDetail",
    "ReportListResponse",
    "ReportRecord",
    "ReportStatus",
    "ReportSubject",
    "ReportSummary",
]
