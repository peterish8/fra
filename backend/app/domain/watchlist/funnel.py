from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Candidate:
    company_id: str
    cohort: str = "UNKNOWN"
    entity_resolved: bool = False
    identity_collision: bool = False
    evidence_coverage: float = 0.0
    score: float | None = None
    provider_available: bool = True
    critical_failure: bool = False
    signals: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FunnelResult:
    broad_count: int
    screened_count: int
    finalists: tuple[Candidate, ...]
    excluded: tuple[dict[str, str], ...]
    degraded: bool = False
    stop_reason: str | None = None


def run_funnel(
    candidates: Iterable[Candidate | Mapping[str, Any]],
    *,
    minimum_evidence: float = 0.4,
    finalist_limit: int = 10,
) -> FunnelResult:
    records = [
        item if isinstance(item, Candidate) else Candidate(**dict(item)) for item in candidates
    ]
    excluded: list[dict[str, str]] = []
    eligible: list[Candidate] = []
    degraded = False
    for item in records:
        reason = None
        if not item.provider_available:
            degraded = True
            reason = "PROVIDER_DEGRADED"
        elif not item.entity_resolved:
            reason = "IDENTITY_UNRESOLVED"
        elif item.identity_collision:
            reason = "IDENTITY_COLLISION"
        elif item.evidence_coverage < minimum_evidence:
            reason = "INSUFFICIENT_EVIDENCE"
        elif item.critical_failure:
            reason = "CRITICAL_PIPELINE_FAILURE"
        if reason:
            excluded.append({"company_id": item.company_id, "reason": reason})
        else:
            eligible.append(item)
    finalists = tuple(
        sorted(eligible, key=lambda item: item.score or 0, reverse=True)[: max(0, finalist_limit)]
    )
    return FunnelResult(
        len(records),
        len(eligible),
        finalists,
        tuple(excluded),
        degraded,
        "NO_QUALIFYING_CANDIDATES" if not finalists else None,
    )
