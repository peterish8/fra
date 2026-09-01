"""Typed fact records used by deterministic verification and calculations."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FactRecord(BaseModel):
    """Persistable fact matching the Truth Ledger ``facts`` table."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: UUID = Field(default_factory=uuid4)
    research_run_id: UUID | None = None
    company_id: UUID | None = None
    source_snapshot_id: UUID
    fact_type: str = Field(min_length=1, max_length=100)
    metric_code: str | None = Field(default=None, max_length=120)
    raw_value_text: str | None = Field(default=None, max_length=2_000)
    numeric_value: Decimal | None = None
    text_value: str | None = Field(default=None, max_length=20_000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    unit: str | None = Field(default=None, max_length=40)
    period_start: date | None = None
    period_end: date | None = None
    period_label: str | None = Field(default=None, max_length=120)
    accounting_basis: str | None = Field(default=None, max_length=40)
    entity_scope: str | None = Field(default=None, max_length=60)
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("numeric_value", mode="before")
    @classmethod
    def reject_boolean_numeric(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("numeric_value cannot be boolean")
        return value

    @field_validator("numeric_value")
    @classmethod
    def reject_non_finite_numeric(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("numeric_value must be finite")
        return value

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class FactInput(BaseModel):
    """Validated input before a fact receives its persistent identity."""

    model_config = ConfigDict(extra="forbid")

    source_snapshot_id: UUID
    research_run_id: UUID | None = None
    company_id: UUID | None = None
    fact_type: str = Field(min_length=1, max_length=100)
    metric_code: str | None = Field(default=None, max_length=120)
    raw_value_text: str | None = Field(default=None, max_length=2_000)
    numeric_value: Decimal | None = None
    text_value: str | None = Field(default=None, max_length=20_000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    unit: str | None = Field(default=None, max_length=40)
    period_start: date | None = None
    period_end: date | None = None
    period_label: str | None = Field(default=None, max_length=120)
    accounting_basis: str | None = Field(default=None, max_length=40)
    entity_scope: str | None = Field(default=None, max_length=60)
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("numeric_value", mode="before")
    @classmethod
    def reject_boolean_numeric(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("numeric_value cannot be boolean")
        return value

    @field_validator("numeric_value")
    @classmethod
    def reject_non_finite_numeric(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("numeric_value must be finite")
        return value


__all__ = ["FactInput", "FactRecord"]
