"""Deterministic financial taxonomy, normalization, and calculations."""

from .calculations import FORMULA_VERSION, calculate_growth, calculate_margin, calculate_ratio
from .models import (
    CalculationRecord,
    CalculationStatus,
    FinancialInput,
    FinancialUnit,
    NormalizedFinancialValue,
    NormalizedPeriod,
    PeriodComparison,
    PeriodComparisonResult,
    PeriodKind,
)
from .normalization import (
    classify_period,
    compare_periods,
    metric_tolerance,
    normalize,
    normalize_financial_value,
    normalize_period,
    normalize_unit,
    normalize_value,
    parse_numeric,
    within_tolerance,
)

__all__ = [
    "FORMULA_VERSION",
    "CalculationRecord",
    "CalculationStatus",
    "FinancialInput",
    "FinancialUnit",
    "NormalizedFinancialValue",
    "NormalizedPeriod",
    "PeriodComparison",
    "PeriodComparisonResult",
    "PeriodKind",
    "calculate_growth",
    "calculate_margin",
    "calculate_ratio",
    "compare_periods",
    "classify_period",
    "metric_tolerance",
    "normalize_financial_value",
    "normalize",
    "normalize_period",
    "normalize_unit",
    "normalize_value",
    "parse_numeric",
    "within_tolerance",
]
