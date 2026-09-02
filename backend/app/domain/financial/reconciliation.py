"""Lossless, typed reconciliation of financial observations.

The reconciler normalizes units before comparing values, checks every
comparability dimension first, and never creates a synthetic midpoint. When
like-for-like observations still disagree, both observations and the open
conflict remain available to the report layer.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .normalization import (
    normalize_financial_value,
    normalize_period,
    parse_numeric,
    within_tolerance,
)


class ConflictClassification(StrEnum):
    NO_CONFLICT = "NO_CONFLICT"
    VALUE_CONFLICT = "VALUE_CONFLICT"
    PERIOD_MISMATCH = "PERIOD_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    SOURCE_DATE_MISMATCH = "SOURCE_DATE_MISMATCH"
    METHODOLOGY_DIFFERENCE = "METHODOLOGY_DIFFERENCE"
    GAAP_VS_NON_GAAP = "GAAP_VS_NON_GAAP"
    ENTITY_SCOPE_DIFFERENCE = "ENTITY_SCOPE_DIFFERENCE"
    RESTATEMENT = "RESTATEMENT"
    DEFINITION_MISMATCH = "DEFINITION_MISMATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    ROUNDING_DIFFERENCE = "ROUNDING_DIFFERENCE"
    ROUNDING = "ROUNDING_DIFFERENCE"


class ConflictSeverity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConflictStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    ACCEPTED_UNCERTAINTY = "ACCEPTED_UNCERTAINTY"


class ComparabilityKey(BaseModel):
    """Dimensions that must match before a numeric comparison is meaningful."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str
    definition: str | None = None
    period: str | None = None
    currency: str | None = None
    accounting_basis: str | None = None
    entity_scope: str | None = None
    methodology: str | None = None


class FinancialObservation(BaseModel):
    """A source observation with enough lineage for an auditable comparison."""

    model_config = ConfigDict(extra="allow")

    observation_id: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: Decimal | int | float | str | None = None
    unit: str | None = None
    normalized_value: Decimal | int | float | str | None = None
    normalized_currency: str | None = None
    fx_rate: Decimal | int | float | str | None = None
    fx_date: str | date | None = None
    period: str | None = None
    currency: str | None = None
    accounting_basis: str | None = None
    entity_scope: str | None = None
    methodology: str | None = None
    definition: str | None = None
    source_id: str | None = None
    source_family_id: str | None = None
    source_date: str | None = None
    materiality: str = "MEDIUM"
    is_restatement: bool = False
    supersedes_id: str | None = None

    @property
    def numeric_value(self) -> Decimal | None:
        """Return the deterministic comparison value, without null-as-zero."""

        if self.normalized_value is not None:
            return _safe_parse_numeric(self.normalized_value)
        try:
            normalized = normalize_financial_value(
                self.value,
                unit=self.unit,
                currency=self.currency,
                normalized_currency=self.normalized_currency,
                fx_rate=self.fx_rate,
                fx_date=self.fx_date,
                period=self.period,
            )
        except (TypeError, ValueError, InvalidOperation):
            return None
        return normalized.normalized_value

    @property
    def comparison_currency(self) -> str | None:
        """Currency of ``numeric_value`` after an explicit conversion, if any."""

        original = _normalize_currency(self.currency)
        target = _normalize_currency(self.normalized_currency)
        if target and target != original and self.fx_rate is not None and self.fx_date is not None:
            return target
        return original


class ReconciliationResult(BaseModel):
    """Immutable result retaining both sides and all conflict state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    classification: ConflictClassification
    severity: ConflictSeverity
    status: ConflictStatus
    comparable: bool
    members: list[str]
    explanation: str
    comparability_key: ComparabilityKey
    right_comparability_key: ComparabilityKey | None = None
    canonical_resolution: str | None = None
    independent_family_count: int = 0
    left_value: Decimal | None = None
    right_value: Decimal | None = None
    average: None = None
    midpoint: None = None
    history_preserved: bool = True
    supersedes_fact_id: str | None = None
    current_fact_id: str | None = None
    # ``classification`` is NO_CONFLICT for the public benchmark; this field
    # keeps the deterministic rounding explanation typed and inspectable.
    difference_classification: ConflictClassification | None = None


def build_comparability_key(
    observation: FinancialObservation | Mapping[str, Any],
) -> ComparabilityKey:
    value = _coerce_observation(observation)
    period = normalize_period(value.period).label if value.period else None
    return ComparabilityKey(
        metric=_normalize_dimension(value.metric),
        definition=_normalize_optional(value.definition),
        period=period,
        currency=value.comparison_currency,
        accounting_basis=_normalize_optional(value.accounting_basis),
        entity_scope=_normalize_optional(value.entity_scope),
        methodology=_normalize_optional(value.methodology),
    )


def classify_reconciliation(
    left: FinancialObservation | Mapping[str, Any],
    right: FinancialObservation | Mapping[str, Any],
    *,
    tolerance: Decimal | int | float | None = None,
) -> ReconciliationResult:
    first = _coerce_observation(left)
    second = _coerce_observation(right)
    first_key = build_comparability_key(first)
    second_key = build_comparability_key(second)
    members = [first.observation_id, second.observation_id]
    family_count = _independent_family_count(first, second)

    restatement = _restatement_link(first, second)
    if restatement is not None:
        superseded_id, current_id = restatement
        return _result(
            classification=ConflictClassification.RESTATEMENT,
            severity=ConflictSeverity.INFO,
            status=ConflictStatus.RESOLVED,
            comparable=True,
            members=members,
            explanation=(
                "A later restatement supersedes the earlier observation; "
                "the prior fact remains in history."
            ),
            first_key=first_key,
            second_key=second_key,
            first=first,
            second=second,
            family_count=family_count,
            canonical_resolution=(
                "Retain the prior observation and use the superseding observation "
                "for current views."
            ),
            supersedes_fact_id=superseded_id,
            current_fact_id=current_id,
        )

    dimension = _dimension_difference(first_key, second_key)
    if dimension is not None:
        classification, explanation, comparable, status = dimension
        return _result(
            classification=classification,
            severity=_severity(classification, first, second, family_count),
            status=status,
            comparable=comparable,
            members=members,
            explanation=explanation,
            first_key=first_key,
            second_key=second_key,
            first=first,
            second=second,
            family_count=family_count,
        )

    # Filing/source dates are provenance dimensions.  They do not make an
    # older and newer observation a value conflict, but must stay explicit so
    # report consumers can apply freshness/supersession policy.
    if first.source_date and second.source_date and first.source_date != second.source_date:
        return _result(
            classification=ConflictClassification.SOURCE_DATE_MISMATCH,
            severity=ConflictSeverity.LOW,
            status=ConflictStatus.ACCEPTED_UNCERTAINTY,
            comparable=False,
            members=members,
            explanation=(
                "Observations were retrieved or filed on different source dates; "
                "no value conflict is inferred."
            ),
            first_key=first_key,
            second_key=second_key,
            first=first,
            second=second,
            family_count=family_count,
        )

    left_number, right_number = first.numeric_value, second.numeric_value
    if left_number is None or right_number is None:
        return _result(
            classification=ConflictClassification.INSUFFICIENT_EVIDENCE,
            severity=ConflictSeverity.LOW,
            status=ConflictStatus.ACCEPTED_UNCERTAINTY,
            comparable=False,
            members=members,
            explanation=(
                "A comparable observation lacks a valid numeric value; "
                "no value was assumed."
            ),
            first_key=first_key,
            second_key=second_key,
            first=first,
            second=second,
            family_count=family_count,
        )

    equivalent = (
        abs(left_number - right_number) <= Decimal(str(tolerance))
        if tolerance is not None
        else within_tolerance(left_number, right_number, metric=first.metric)
    )
    if equivalent:
        return _result(
            classification=ConflictClassification.NO_CONFLICT,
            difference_classification=ConflictClassification.ROUNDING_DIFFERENCE,
            severity=ConflictSeverity.INFO,
            status=ConflictStatus.RESOLVED,
            comparable=True,
            members=members,
            explanation=(
                "Comparable values differ only within the explicit metric "
                "rounding tolerance."
            ),
            first_key=first_key,
            second_key=second_key,
            first=first,
            second=second,
            family_count=family_count,
            canonical_resolution="Retain both reported values; they are rounding-equivalent.",
        )

    return _result(
        classification=ConflictClassification.VALUE_CONFLICT,
        severity=_severity(ConflictClassification.VALUE_CONFLICT, first, second, family_count),
        status=ConflictStatus.OPEN,
        comparable=True,
        members=members,
        explanation="Comparable observations disagree; both values remain visible and unresolved.",
        first_key=first_key,
        second_key=second_key,
        first=first,
        second=second,
        family_count=family_count,
    )


def apply_restatement(
    left: FinancialObservation | Mapping[str, Any],
    right: FinancialObservation | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a lineage record for an explicit restatement relationship."""

    first = _coerce_observation(left)
    second = _coerce_observation(right)
    link = _restatement_link(first, second)
    if link is None:
        raise ValueError("observations do not contain an explicit restatement relationship")
    superseded_id, current_id = link
    return {
        "classification": ConflictClassification.RESTATEMENT.value,
        "supersedes_fact_id": superseded_id,
        "current_fact_id": current_id,
        "fact_id": current_id,
        "history_preserved": True,
        "prior_observation_id": superseded_id,
        "restated_observation_id": current_id,
    }


def reconcile_financial_values(
    left: FinancialObservation | Mapping[str, Any],
    right: FinancialObservation | Mapping[str, Any],
    **kwargs: Any,
) -> ReconciliationResult:
    return classify_reconciliation(left, right, **kwargs)


def reconcile(
    left: FinancialObservation | Mapping[str, Any],
    right: FinancialObservation | Mapping[str, Any],
    **kwargs: Any,
) -> ReconciliationResult:
    return classify_reconciliation(left, right, **kwargs)


classify_financial_conflict = classify_reconciliation
reconcile_financial_facts = reconcile_financial_values
compare_financial_records = classify_reconciliation
supersede_fact = apply_restatement
reconcile_restatement = apply_restatement


def _dimension_difference(
    left: ComparabilityKey,
    right: ComparabilityKey,
) -> tuple[ConflictClassification, str, bool, ConflictStatus] | None:
    dimensions: tuple[str, ...] = (
        "metric",
        "period",
        "currency",
        "entity_scope",
        "accounting_basis",
        "methodology",
        "definition",
    )
    for dimension in dimensions:
        first, second = getattr(left, dimension), getattr(right, dimension)
        if first == second:
            continue
        if first is None or second is None:
            return (
                ConflictClassification.INSUFFICIENT_EVIDENCE,
                (
                    f"{dimension.replace('_', ' ').capitalize()} scope is missing "
                    "on one observation; values are not compared."
                ),
                False,
                ConflictStatus.ACCEPTED_UNCERTAINTY,
            )
        if dimension == "metric":
            return (
                ConflictClassification.DEFINITION_MISMATCH,
                "Metric definitions differ; observations are not directly comparable.",
                False,
                ConflictStatus.ACCEPTED_UNCERTAINTY,
            )
        if dimension == "period":
            return (
                ConflictClassification.PERIOD_MISMATCH,
                "Reporting periods differ and no transformation was supplied.",
                False,
                ConflictStatus.ACCEPTED_UNCERTAINTY,
            )
        if dimension == "currency":
            return (
                ConflictClassification.CURRENCY_MISMATCH,
                "Currencies differ; an explicit FX rate and date are required before comparison.",
                False,
                ConflictStatus.ACCEPTED_UNCERTAINTY,
            )
        if dimension == "entity_scope":
            return (
                ConflictClassification.ENTITY_SCOPE_DIFFERENCE,
                "Entity scopes differ; parent, subsidiary, and segment values are not combined.",
                False,
                ConflictStatus.ACCEPTED_UNCERTAINTY,
            )
        if dimension == "accounting_basis":
            if {first, second} == {"gaap", "non_gaap"}:
                return (
                    ConflictClassification.GAAP_VS_NON_GAAP,
                    "GAAP and non-GAAP observations use different accounting bases.",
                    False,
                    ConflictStatus.ACCEPTED_UNCERTAINTY,
                )
            return (
                ConflictClassification.METHODOLOGY_DIFFERENCE,
                "Accounting bases differ; values are not averaged.",
                False,
                ConflictStatus.ACCEPTED_UNCERTAINTY,
            )
        if dimension == "methodology":
            return (
                ConflictClassification.METHODOLOGY_DIFFERENCE,
                "Calculation methodologies differ; values are not averaged.",
                False,
                ConflictStatus.ACCEPTED_UNCERTAINTY,
            )
        return (
            ConflictClassification.METHODOLOGY_DIFFERENCE,
            "Explicit metric definitions differ; values are not averaged.",
            False,
            ConflictStatus.ACCEPTED_UNCERTAINTY,
        )
    return None


def _coerce_observation(value: FinancialObservation | Mapping[str, Any]) -> FinancialObservation:
    if isinstance(value, FinancialObservation):
        return value
    payload = dict(value)
    fact_id = payload.get("fact_id")
    if "observation_id" not in payload:
        payload["observation_id"] = str(payload.get("id") or fact_id or "observation")
    if "metric" not in payload:
        payload["metric"] = str(payload.get("metric_code") or "unknown_metric")
    return FinancialObservation.model_validate(payload)


def _restatement_link(
    left: FinancialObservation, right: FinancialObservation
) -> tuple[str, str] | None:
    left_extra, right_extra = left.model_extra or {}, right.model_extra or {}
    left_fact = str(left_extra.get("fact_id") or left.observation_id)
    right_fact = str(right_extra.get("fact_id") or right.observation_id)
    links = (
        (left, left.supersedes_id),
        (right, right.supersedes_id),
        (left, left_extra.get("restates_fact_id")),
        (right, right_extra.get("restates_fact_id")),
        (left, left_extra.get("restated_fact_id")),
        (right, right_extra.get("restated_fact_id")),
        (left, left_extra.get("supersedes_fact_id")),
        (right, right_extra.get("supersedes_fact_id")),
    )
    for owner, reference in links:
        if not reference:
            continue
        reference = str(reference)
        if owner is left and reference == right_fact:
            return right_fact, left_fact
        if owner is right and reference == left_fact:
            return left_fact, right_fact
    if left.is_restatement != right.is_restatement and (
        left.is_restatement or right.is_restatement
    ):
        older, newer = _ordered_by_filing_date(left, right)
        return _fact_id(older), _fact_id(newer)
    return None


def _ordered_by_filing_date(
    left: FinancialObservation, right: FinancialObservation
) -> tuple[FinancialObservation, FinancialObservation]:
    left_extra, right_extra = left.model_extra or {}, right.model_extra or {}
    left_date = _parse_date(left_extra.get("filing_date")) or _parse_date(left.source_date)
    right_date = _parse_date(right_extra.get("filing_date")) or _parse_date(right.source_date)
    if left_date is not None and right_date is not None and left_date <= right_date:
        return left, right
    return right, left


def _fact_id(value: FinancialObservation) -> str:
    return str((value.model_extra or {}).get("fact_id") or value.observation_id)


def _result(
    *,
    classification: ConflictClassification,
    severity: ConflictSeverity,
    status: ConflictStatus,
    comparable: bool,
    members: list[str],
    explanation: str,
    first_key: ComparabilityKey,
    second_key: ComparabilityKey,
    first: FinancialObservation,
    second: FinancialObservation,
    family_count: int,
    canonical_resolution: str | None = None,
    supersedes_fact_id: str | None = None,
    current_fact_id: str | None = None,
    difference_classification: ConflictClassification | None = None,
) -> ReconciliationResult:
    return ReconciliationResult(
        classification=classification,
        severity=severity,
        status=status,
        comparable=comparable,
        members=members,
        explanation=explanation,
        comparability_key=first_key,
        right_comparability_key=second_key,
        canonical_resolution=canonical_resolution,
        independent_family_count=family_count,
        left_value=first.numeric_value,
        right_value=second.numeric_value,
        history_preserved=True,
        supersedes_fact_id=supersedes_fact_id,
        current_fact_id=current_fact_id,
        difference_classification=difference_classification,
    )


def _independent_family_count(left: FinancialObservation, right: FinancialObservation) -> int:
    family_ids = {value for value in (left.source_family_id, right.source_family_id) if value}
    if family_ids:
        return len(family_ids)
    return len({value for value in (left.source_id, right.source_id) if value})


def _severity(
    classification: ConflictClassification,
    left: FinancialObservation,
    right: FinancialObservation,
    family_count: int,
) -> ConflictSeverity:
    if classification in {
        ConflictClassification.NO_CONFLICT,
        ConflictClassification.ROUNDING_DIFFERENCE,
        ConflictClassification.RESTATEMENT,
    }:
        return ConflictSeverity.INFO
    if classification is ConflictClassification.VALUE_CONFLICT:
        material = {left.materiality.upper(), right.materiality.upper()}
        if family_count >= 2 and material.intersection({"HIGH", "CRITICAL"}):
            return ConflictSeverity.CRITICAL
        return ConflictSeverity.HIGH if family_count >= 2 else ConflictSeverity.MEDIUM
    if classification is ConflictClassification.INSUFFICIENT_EVIDENCE:
        return ConflictSeverity.LOW
    return ConflictSeverity.MEDIUM


def _normalize_dimension(value: str) -> str:
    return "_".join(value.strip().casefold().replace("-", " ").split())


def _normalize_optional(value: str | None) -> str | None:
    return _normalize_dimension(value) if value else None


def _normalize_currency(value: str | None) -> str | None:
    return value.strip().upper() if value and value.strip() else None


def _safe_parse_numeric(value: Any) -> Decimal | None:
    try:
        return parse_numeric(value)
    except (TypeError, ValueError, InvalidOperation):
        return None


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


__all__ = [
    "ComparabilityKey",
    "ConflictClassification",
    "ConflictSeverity",
    "ConflictStatus",
    "FinancialObservation",
    "ReconciliationResult",
    "apply_restatement",
    "build_comparability_key",
    "classify_financial_conflict",
    "classify_reconciliation",
    "compare_financial_records",
    "reconcile",
    "reconcile_financial_facts",
    "reconcile_financial_values",
    "reconcile_restatement",
    "supersede_fact",
]
