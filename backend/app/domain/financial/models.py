"""Provider-neutral financial value and calculation models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FinancialUnit(StrEnum):
    UNKNOWN = "UNKNOWN"
    RAW = "RAW"
    THOUSAND = "THOUSAND"
    MILLION = "MILLION"
    BILLION = "BILLION"
    LAKH = "LAKH"
    CRORE = "CRORE"
    PERCENT = "PERCENT"
    BASIS_POINTS = "BASIS_POINTS"


class PeriodKind(StrEnum):
    FISCAL_YEAR = "FISCAL_YEAR"
    CALENDAR_YEAR = "CALENDAR_YEAR"
    QUARTER = "QUARTER"
    TTM = "TTM"
    DATE_RANGE = "DATE_RANGE"
    UNKNOWN = "UNKNOWN"


class PeriodComparison(StrEnum):
    MATCH = "MATCH"
    PERIOD_MISMATCH = "PERIOD_MISMATCH"
    UNKNOWN = "UNKNOWN"


class NormalizedPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: PeriodKind
    label: str | None = None
    start: date | None = None
    end: date | None = None


class NormalizedFinancialValue(BaseModel):
    """A value retaining its source representation and deterministic result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    original_value: Decimal | None
    original_text: str | None = None
    original_unit: FinancialUnit
    normalized_value: Decimal | None
    normalized_unit: FinancialUnit
    original_currency: str | None = None
    normalized_currency: str | None = None
    fx_rate: Decimal | None = None
    fx_date: str | None = None
    period: NormalizedPeriod | None = None
    status: str = "NORMALIZED"

    @property
    def value(self) -> Decimal | None:
        return self.normalized_value


class CalculationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NOT_REPORTED = "NOT_REPORTED"
    DIVIDE_BY_ZERO = "DIVIDE_BY_ZERO"
    PERIOD_MISMATCH = "PERIOD_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"


class CalculationRecord(BaseModel):
    """Auditable deterministic derivation record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    formula: str
    formula_version: str
    inputs: dict[str, Decimal | None]
    output: Decimal | None
    status: CalculationStatus
    metric: str | None = None
    period: NormalizedPeriod | None = None
    tolerance: Decimal | None = None
    # Compatibility fields make records consumable by report/calculation
    # workers that use ``result`` or ``value`` terminology.
    result: Any | None = None
    value: Any | None = None


class FinancialInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1, max_length=120)
    value: str | int | float | Decimal | None
    unit: FinancialUnit = FinancialUnit.RAW
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    period: str | None = None
    entity_scope: str | None = None
    accounting_basis: str | None = None

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class PeriodComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    comparison: PeriodComparison
    reason: str


__all__ = [
    "CalculationRecord",
    "CalculationStatus",
    "FinancialInput",
    "FinancialUnit",
    "NormalizedFinancialValue",
    "NormalizedPeriod",
    "PeriodComparison",
    "PeriodComparisonResult",
    "PeriodKind",
]
