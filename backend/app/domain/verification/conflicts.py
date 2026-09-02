"""Canonical conflict records and comparability grouping."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.financial.reconciliation import (
    ComparabilityKey,
    ConflictClassification,
    ConflictSeverity,
    ConflictStatus,
    FinancialObservation,
    ReconciliationResult,
    apply_restatement,
    build_comparability_key,
    classify_reconciliation,
)


class ConflictCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    members: list[FinancialObservation] = Field(min_length=2)


ConflictRecord = ReconciliationResult


def group_comparable_observations(
    observations: Iterable[FinancialObservation | Mapping[str, Any]],
) -> dict[ComparabilityKey, list[FinancialObservation]]:
    """Group observations only when all comparison dimensions are equal."""

    grouped: defaultdict[ComparabilityKey, list[FinancialObservation]] = defaultdict(list)
    for index, raw in enumerate(observations):
        if isinstance(raw, FinancialObservation):
            observation = raw
        else:
            payload = dict(raw)
            payload.setdefault(
                "observation_id",
                str(payload.get("id") or payload.get("fact_id") or f"observation-{index}"),
            )
            payload.setdefault("metric", str(payload.get("metric_code") or "unknown_metric"))
            observation = FinancialObservation.model_validate(payload)
        grouped[build_comparability_key(observation)].append(observation)
    return dict(grouped)


def classify_conflict(
    left: FinancialObservation | Mapping[str, Any],
    right: FinancialObservation | Mapping[str, Any],
    **kwargs: Any,
) -> ConflictRecord:
    return classify_reconciliation(left, right, **kwargs)


# Compatibility entry points used by workers and the benchmark contract.
classify_financial_conflict = classify_conflict
reconcile_financial_facts = classify_conflict
compare_financial_records = classify_conflict
reconcile_restatement = apply_restatement
supersede_fact = apply_restatement


def evaluate_conflict(
    candidate: ConflictCandidate | Mapping[str, Any] | FinancialObservation,
    other: FinancialObservation | Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ConflictRecord:
    """Evaluate a pair, or a fixture object containing ``left`` and ``right``."""

    if other is not None:
        return classify_reconciliation(candidate, other, **kwargs)  # type: ignore[arg-type]
    if isinstance(candidate, ConflictCandidate):
        if len(candidate.members) != 2:
            raise ValueError("exactly two observations are required")
        return classify_reconciliation(candidate.members[0], candidate.members[1], **kwargs)
    if isinstance(candidate, Mapping):
        if "left" in candidate and "right" in candidate:
            return classify_reconciliation(candidate["left"], candidate["right"], **kwargs)
        members = candidate.get("members")
        if (
            isinstance(members, Sequence)
            and not isinstance(members, (str, bytes))
            and len(members) == 2
        ):
            return classify_reconciliation(members[0], members[1], **kwargs)
    raise ValueError("conflict evaluation requires left/right observations")


def unresolved_conflict(result: ReconciliationResult) -> bool:
    return result.status is ConflictStatus.OPEN


__all__ = [
    "ComparabilityKey",
    "ConflictCandidate",
    "ConflictClassification",
    "ConflictRecord",
    "ConflictSeverity",
    "ConflictStatus",
    "FinancialObservation",
    "apply_restatement",
    "build_comparability_key",
    "classify_conflict",
    "classify_financial_conflict",
    "compare_financial_records",
    "evaluate_conflict",
    "group_comparable_observations",
    "reconcile_financial_facts",
    "reconcile_restatement",
    "supersede_fact",
    "unresolved_conflict",
]
