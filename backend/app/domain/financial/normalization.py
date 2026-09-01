"""Pure, deterministic normalization of reported financial values."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from .models import (
    FinancialUnit,
    NormalizedFinancialValue,
    NormalizedPeriod,
    PeriodComparison,
    PeriodComparisonResult,
    PeriodKind,
)

_UNIT_FACTORS: dict[FinancialUnit, Decimal] = {
    FinancialUnit.RAW: Decimal("1"),
    FinancialUnit.UNKNOWN: Decimal("1"),
    FinancialUnit.THOUSAND: Decimal("1000"),
    FinancialUnit.MILLION: Decimal("1000000"),
    FinancialUnit.BILLION: Decimal("1000000000"),
    FinancialUnit.LAKH: Decimal("100000"),
    FinancialUnit.CRORE: Decimal("10000000"),
    FinancialUnit.PERCENT: Decimal("0.01"),
    FinancialUnit.BASIS_POINTS: Decimal("0.0001"),
}
_UNIT_ALIASES: dict[str, FinancialUnit] = {
    "": FinancialUnit.RAW,
    "raw": FinancialUnit.RAW,
    "unit": FinancialUnit.RAW,
    "k": FinancialUnit.THOUSAND,
    "thousand": FinancialUnit.THOUSAND,
    "thousands": FinancialUnit.THOUSAND,
    "m": FinancialUnit.MILLION,
    "mm": FinancialUnit.MILLION,
    "mn": FinancialUnit.MILLION,
    "million": FinancialUnit.MILLION,
    "millions": FinancialUnit.MILLION,
    "b": FinancialUnit.BILLION,
    "bn": FinancialUnit.BILLION,
    "billion": FinancialUnit.BILLION,
    "billions": FinancialUnit.BILLION,
    "lakh": FinancialUnit.LAKH,
    "lakhs": FinancialUnit.LAKH,
    "lac": FinancialUnit.LAKH,
    "crore": FinancialUnit.CRORE,
    "crores": FinancialUnit.CRORE,
    "%": FinancialUnit.PERCENT,
    "percent": FinancialUnit.PERCENT,
    "percentage": FinancialUnit.PERCENT,
    "bps": FinancialUnit.BASIS_POINTS,
    "basis_points": FinancialUnit.BASIS_POINTS,
}


def normalize_unit(unit: str | FinancialUnit | None) -> FinancialUnit:
    if isinstance(unit, FinancialUnit):
        return unit
    if unit is None:
        return FinancialUnit.UNKNOWN
    key = unit.strip().casefold().replace(" ", "_")
    try:
        return _UNIT_ALIASES[key]
    except KeyError as error:
        raise ValueError(f"unsupported financial unit: {unit}") from error


def parse_numeric(value: str | int | float | Decimal | None) -> Decimal | None:
    """Parse source notation without turning an absent value into zero."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a financial number")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except InvalidOperation as error:
            raise ValueError("invalid financial number") from error
    text = value.strip()
    if not text or text.casefold() in {"n/a", "na", "not reported", "null", "-"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?", text)
    if match is None:
        raise ValueError(f"invalid financial number: {value}")
    text = match.group(0).replace(",", "")
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"invalid financial number: {value}") from error
    return -number if negative else number


def normalize_financial_value(
    value: str | int | float | Decimal | None,
    *,
    unit: str | FinancialUnit | None = FinancialUnit.RAW,
    currency: str | None = None,
    normalized_currency: str | None = None,
    target_currency: str | None = None,
    fx_rate: Decimal | int | float | str | None = None,
    fx_date: date | str | None = None,
    period: str | NormalizedPeriod | None = None,
) -> NormalizedFinancialValue:
    source_unit = normalize_unit(unit)
    original = parse_numeric(value)
    rate = parse_numeric(fx_rate)
    target = normalized_currency or target_currency
    if target and target.upper() != (currency or "").upper() and rate is None:
        raise ValueError("explicit FX rate is required for currency conversion")
    if (
        target
        and target.upper() != (currency or "").upper()
        and rate is not None
        and fx_date is None
    ):
        raise ValueError("FX date is required for currency conversion")
    normalized = None if original is None else original * _UNIT_FACTORS[source_unit]
    if rate is not None:
        normalized = None if normalized is None else normalized * rate
    source_currency = currency.upper() if currency else None
    target_currency_value = target.upper() if target else source_currency
    fx_date_value = fx_date.isoformat() if isinstance(fx_date, date) else fx_date
    parsed_period = normalize_period(period) if isinstance(period, str) else period
    return NormalizedFinancialValue(
        original_value=original,
        original_text=str(value) if value is not None else None,
        original_unit=source_unit,
        normalized_value=normalized,
        normalized_unit=(
            FinancialUnit.UNKNOWN
            if source_unit is FinancialUnit.UNKNOWN
            else (
                FinancialUnit.PERCENT
                if source_unit in {FinancialUnit.PERCENT, FinancialUnit.BASIS_POINTS}
                else FinancialUnit.RAW
            )
        ),
        original_currency=source_currency,
        normalized_currency=target_currency_value,
        fx_rate=rate,
        fx_date=fx_date_value,
        period=parsed_period,
        status="NOT_REPORTED" if original is None else "NORMALIZED",
    )


def normalize_period(period: str | None) -> NormalizedPeriod:
    if period is None or not period.strip():
        return NormalizedPeriod(kind=PeriodKind.UNKNOWN, label=None)
    label = " ".join(period.strip().upper().split())
    if re.fullmatch(r"FY\s*\d{4}", label):
        return NormalizedPeriod(kind=PeriodKind.FISCAL_YEAR, label=label.replace(" ", ""))
    if re.fullmatch(r"CY\s*\d{4}", label):
        return NormalizedPeriod(kind=PeriodKind.CALENDAR_YEAR, label=label.replace(" ", ""))
    if re.fullmatch(r"(?:Q[1-4]\s*)?(?:FY|CY)\s*\d{4}", label) and label.startswith("Q"):
        return NormalizedPeriod(kind=PeriodKind.QUARTER, label=label.replace(" ", ""))
    if re.fullmatch(r"Q[1-4](?:\s+FY|\s+CY)?\s*\d{4}", label):
        return NormalizedPeriod(kind=PeriodKind.QUARTER, label=label.replace(" ", ""))
    if label == "TTM" or label.startswith("TTM ") or label in {"LTM", "TRAILING TWELVE MONTHS"}:
        return NormalizedPeriod(kind=PeriodKind.TTM, label="TTM")
    return NormalizedPeriod(kind=PeriodKind.DATE_RANGE, label=label)


def compare_periods(
    left: NormalizedPeriod | str | None, right: NormalizedPeriod | str | None
) -> PeriodComparisonResult:
    left_period = normalize_period(left) if isinstance(left, str) or left is None else left
    right_period = normalize_period(right) if isinstance(right, str) or right is None else right
    if left_period.kind is PeriodKind.UNKNOWN or right_period.kind is PeriodKind.UNKNOWN:
        return PeriodComparisonResult(
            comparison=PeriodComparison.UNKNOWN, reason="A reporting period is unknown."
        )
    if left_period.label == right_period.label and left_period.kind is right_period.kind:
        return PeriodComparisonResult(
            comparison=PeriodComparison.MATCH, reason="Reporting periods match."
        )
    return PeriodComparisonResult(
        comparison=PeriodComparison.PERIOD_MISMATCH, reason="Reporting periods differ."
    )


def metric_tolerance(metric: str | None) -> Decimal:
    normalized = (metric or "").casefold()
    if "margin" in normalized or "rate" in normalized or "percent" in normalized:
        return Decimal("0.0005")
    if "share" in normalized or "per_share" in normalized:
        return Decimal("0.01")
    return Decimal("0.005")


def within_tolerance(left: Decimal, right: Decimal, *, metric: str | None = None) -> bool:
    tolerance = metric_tolerance(metric)
    scale = max(abs(left), abs(right), Decimal("1"))
    return abs(left - right) <= tolerance * scale


normalize_value = normalize_financial_value
normalize = normalize_financial_value
classify_period = normalize_period


__all__ = [
    "compare_periods",
    "metric_tolerance",
    "normalize_financial_value",
    "normalize_period",
    "normalize_unit",
    "parse_numeric",
    "within_tolerance",
]
