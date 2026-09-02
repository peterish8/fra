"""Private deterministic helpers shared by score engines."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .models import ScoreDimension, ScoreResult, ScoreStatus


def as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return vars(value)
    raise TypeError("score input must be a mapping or typed model")


def first(value: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in value and value[key] is not None:
            return value[key]
    return default


def number(value: Any, *, none_values: frozenset[str] = frozenset()) -> float | None:
    if value is None or isinstance(value, bool):
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        return None
    if isinstance(value, str):
        normalized = value.strip().upper().replace("-", "_")
        if normalized in none_values or normalized in {"NA", "N_A", "NOT_APPLICABLE", "UNKNOWN"}:
            return None
        if normalized in {"PASS", "PASSED", "VERIFIED", "CURRENT", "DIRECT", "STRONG"}:
            return 1.0
        if normalized in {"PARTIAL", "PARTIALLY_SUPPORTED", "AGING", "MEDIUM"}:
            return 0.6
        if normalized in {"FAIL", "FAILED", "CONTRADICTED", "STALE", "NONE"}:
            return 0.0
        try:
            value = float(value)
        except ValueError:
            return None
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return None


def config_hash(config: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(config), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def weighted_dimensions(
    values: list[tuple[str, float, float | None, str]],
) -> tuple[float | None, list[ScoreDimension]]:
    total_weight = sum(weight for _, weight, value, _ in values if value is not None)
    if total_weight <= 0:
        return None, [
            ScoreDimension(
                key=key,
                weight=weight,
                value=value,
                status="NOT_APPLICABLE" if value is None else "EXCLUDED",
                explanation=explanation,
            )
            for key, weight, value, explanation in values
        ]
    dimensions: list[ScoreDimension] = []
    score = 0.0
    for key, weight, value, explanation in values:
        included = value is not None
        normalized_weight = weight / total_weight if included else 0.0
        contribution = (value or 0.0) * normalized_weight * 100
        score += contribution
        dimensions.append(
            ScoreDimension(
                key=key,
                weight=weight,
                value=value,
                normalized_weight=normalized_weight,
                contribution=contribution,
                status="INCLUDED" if included else "NOT_APPLICABLE",
                explanation=explanation,
            )
        )
    return round(score, 3), dimensions


def result(
    *,
    score: float | None,
    status: ScoreStatus,
    method: str,
    score_version: str,
    coverage: float,
    breakdown: dict[str, Any],
    input_ids: tuple[str, ...] = (),
    config: Mapping[str, Any],
    explanation: str,
) -> ScoreResult:
    return ScoreResult(
        score=None if score is None else round(min(100.0, max(0.0, score)), 3),
        status=status,
        method=method,
        score_version=score_version,
        coverage=round(min(100.0, max(0.0, coverage)), 3),
        coverage_factor=round(min(1.0, max(0.0, coverage / 100)), 6),
        breakdown=breakdown,
        input_ids=tuple(input_ids),
        config_hash=config_hash(config),
        explanation=explanation,
    )


__all__ = [
    "as_mapping",
    "config_hash",
    "first",
    "number",
    "result",
    "weighted_dimensions",
]
