"""Deterministic, versioned financial calculations."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .models import CalculationRecord, CalculationStatus, NormalizedPeriod
from .normalization import compare_periods

FORMULA_VERSION = "financial-formulas-v1"


def calculate_growth(
    current: Decimal | int | float | None,
    previous: Decimal | int | float | None,
    *,
    current_period: NormalizedPeriod | str | None = None,
    previous_period: NormalizedPeriod | str | None = None,
    formula_version: str = FORMULA_VERSION,
    metric: str | None = None,
) -> CalculationRecord:
    """Return ``(current - previous) / previous`` without zero fabrication."""

    inputs = {"current": _decimal(current), "previous": _decimal(previous)}
    mismatch = _period_mismatch(current_period, previous_period)
    if mismatch:
        return _record(
            "growth", formula_version, inputs, None, CalculationStatus.PERIOD_MISMATCH, metric
        )
    if inputs["current"] is None or inputs["previous"] is None:
        return _record(
            "growth", formula_version, inputs, None, CalculationStatus.NOT_REPORTED, metric
        )
    if inputs["previous"] == 0:
        return _record(
            "growth", formula_version, inputs, None, CalculationStatus.DIVIDE_BY_ZERO, metric
        )
    return _record(
        "growth",
        formula_version,
        inputs,
        (inputs["current"] - inputs["previous"]) / inputs["previous"],
        CalculationStatus.SUCCESS,
        metric,
    )


def calculate_margin(
    numerator: Decimal | int | float | None,
    denominator: Decimal | int | float | None,
    *,
    formula_version: str = FORMULA_VERSION,
    metric: str | None = "margin",
) -> CalculationRecord:
    return _ratio("margin", numerator, denominator, formula_version, metric)


def calculate_ratio(
    numerator: Decimal | int | float | None,
    denominator: Decimal | int | float | None,
    *,
    formula_version: str = FORMULA_VERSION,
    metric: str | None = "ratio",
) -> CalculationRecord:
    return _ratio("ratio", numerator, denominator, formula_version, metric)


def _ratio(
    formula: str,
    numerator: Decimal | int | float | None,
    denominator: Decimal | int | float | None,
    formula_version: str,
    metric: str | None,
) -> CalculationRecord:
    inputs = {"numerator": _decimal(numerator), "denominator": _decimal(denominator)}
    if inputs["numerator"] is None or inputs["denominator"] is None:
        status = CalculationStatus.NOT_REPORTED
        output = None
    elif inputs["denominator"] == 0:
        status = CalculationStatus.DIVIDE_BY_ZERO
        output = None
    else:
        status = CalculationStatus.SUCCESS
        output = inputs["numerator"] / inputs["denominator"]
    return _record(formula, formula_version, inputs, output, status, metric)


def _decimal(value: Decimal | int | float | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a financial number")
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("invalid financial number") from error


def _period_mismatch(
    current: NormalizedPeriod | str | None, previous: NormalizedPeriod | str | None
) -> bool:
    if current is None or previous is None:
        return False
    return compare_periods(current, previous).comparison.value == "PERIOD_MISMATCH"


def _record(
    formula: str,
    formula_version: str,
    inputs: dict[str, Decimal | None],
    output: Decimal | None,
    status: CalculationStatus,
    metric: str | None,
) -> CalculationRecord:
    return CalculationRecord(
        formula=formula,
        formula_version=formula_version,
        inputs=inputs,
        output=output,
        status=status,
        metric=metric,
        result=output,
        value=output,
    )


def calculate_financial(case: dict[str, Any]) -> CalculationRecord | dict[str, Any]:
    """Execute one fixture/API operation with a versioned audit record."""

    operation = str(case.get("operation", "")).casefold()
    if operation == "growth":
        record = calculate_growth(case.get("current"), case.get("prior"))
    elif operation == "margin":
        record = calculate_margin(case.get("numerator"), case.get("denominator"))
    elif operation == "ratio":
        record = calculate_ratio(case.get("numerator"), case.get("denominator"))
    elif operation == "compare":
        left = _decimal(case.get("left"))
        right = _decimal(case.get("right"))
        tolerance = _decimal(case.get("tolerance"))
        if left is None or right is None or tolerance is None:
            raise ValueError("INSUFFICIENT_DATA")
        result = abs(left - right) <= tolerance
        return {
            "formula": "tolerance_compare",
            "formula_version": FORMULA_VERSION,
            "inputs": case,
            "result": result,
            "value": result,
        }
    else:
        raise ValueError(f"unsupported financial operation: {operation}")
    if record.status is CalculationStatus.DIVIDE_BY_ZERO:
        raise ValueError("DIVIDE_BY_ZERO")
    if record.status is CalculationStatus.NOT_REPORTED:
        raise ValueError("INSUFFICIENT_DATA")
    return record


calculate = calculate_financial
derive = calculate_financial


__all__ = [
    "FORMULA_VERSION",
    "calculate_growth",
    "calculate_financial",
    "calculate_margin",
    "calculate_ratio",
    "calculate",
    "derive",
]
