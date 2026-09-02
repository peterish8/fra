"""Bounded evidence-gap follow-up planning and lineage-safe retrieval loops."""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FollowUpStopReason(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    NO_PROGRESS = "NO_PROGRESS"
    LOOP_BUDGET_EXCEEDED = "LOOP_BUDGET_EXCEEDED"
    LOOP_BUDGET = "LOOP_BUDGET_EXCEEDED"
    PROVIDER_DEGRADED = "PROVIDER_DEGRADED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


class ProviderDegradedError(RuntimeError):
    """A provider cannot supply this follow-up without unsafe assumptions."""


class EvidenceReference(BaseModel):
    """Immutable reference added to an existing claim lineage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: UUID | str
    claim_id: UUID | str
    source_snapshot_id: UUID | str | None = None
    role: str = "SUPPORTS"
    supersedes_evidence_id: UUID | str | None = None


class EvidenceGap(BaseModel):
    """Deterministic reasons a claim needs another bounded research pass."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: UUID | str
    claim_statement: str = ""
    materiality: str = "MEDIUM"
    reasons: tuple[str, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()
    source_family_count: int = Field(default=0, ge=0)
    sufficient: bool = False
    provider_degraded: bool = False

    @field_validator("claim_statement")
    @classmethod
    def normalize_statement(cls, value: str) -> str:
        return value.strip()

    @field_validator("reasons", mode="before")
    @classmethod
    def normalize_reasons(cls, value: Iterable[str]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                str(item).strip().upper() for item in value if str(item).strip()
            )
        )


class FollowUpQuery(BaseModel):
    """A targeted query tied to the original claim, not a new claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: UUID | str
    query: str = Field(min_length=1, max_length=2_000)
    intent: str = Field(min_length=1, max_length=240)
    loop_index: int = Field(ge=1)
    preferred_source_types: tuple[str, ...] = ()


class FollowUpIteration(BaseModel):
    """One bounded retrieval/verification attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    loop_index: int = Field(ge=1)
    queries: tuple[FollowUpQuery, ...]
    added_evidence_ids: tuple[UUID | str, ...] = ()
    lineage_size: int = Field(ge=0)
    progress: bool
    stop_reason: FollowUpStopReason | None = None


class FollowUpResult(BaseModel):
    """Terminal, inspectable result of a bounded follow-up run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: UUID | str
    stop_reason: FollowUpStopReason
    iterations: tuple[FollowUpIteration, ...] = ()
    evidence_lineage: tuple[EvidenceReference, ...] = ()
    partial: bool = True

    @property
    def terminated(self) -> bool:
        return True

    @property
    def loops(self) -> int:
        return len(self.iterations)

    @property
    def lineage(self) -> tuple[EvidenceReference, ...]:
        return self.evidence_lineage

    @property
    def queries(self) -> tuple[FollowUpQuery, ...]:
        return tuple(query for iteration in self.iterations for query in iteration.queries)

    @property
    def history_preserved(self) -> bool:
        return True

    @property
    def loop_count(self) -> int:
        return len(self.iterations)


class EvidenceGapPlanner:
    """Generate a small deterministic query set from typed gap reasons."""

    def __init__(self, *, max_queries: int = 4) -> None:
        if max_queries < 1:
            raise ValueError("max_queries must be positive")
        self.max_queries = max_queries

    def plan(self, gap: EvidenceGap, *, loop_index: int) -> tuple[FollowUpQuery, ...]:
        if loop_index < 1:
            raise ValueError("loop_index must be positive")
        if gap.sufficient or gap.provider_degraded:
            return ()
        statement = gap.claim_statement or f"claim {gap.claim_id}"
        reasons = gap.reasons or ("UNSUPPORTED",)
        queries: list[FollowUpQuery] = []
        templates = {
            "UNSUPPORTED": (
                f'Find independent evidence that directly assesses: "{statement}"',
                "Find direct independent support",
                ("REGULATORY_FILING", "INDEPENDENT_NEWS"),
            ),
            "PARTIAL": (
                f'Find evidence clarifying the unsupported part of: "{statement}"',
                "Clarify partial support",
                ("REGULATORY_FILING", "INDEPENDENT_RESEARCH"),
            ),
            "HIGH_AUTHORITY_CONFLICT": (
                "Find the authoritative definition and period resolving "
                f'this conflict: "{statement}"',
                "Resolve high-authority conflict",
                ("REGULATORY_FILING", "OFFICIAL_REGISTRY"),
            ),
            "NUMERIC_FAILURE": (
                "Find a primary source that reports the comparable numeric "
                f'fact for: "{statement}"',
                "Recheck numeric fact",
                ("REGULATORY_FILING", "FINANCIAL_DATA"),
            ),
            "PERIOD_FAILURE": (
                f'Find a source confirming the reporting period and value for: "{statement}"',
                "Recheck reporting period",
                ("REGULATORY_FILING", "FINANCIAL_DATA"),
            ),
            "LOW_INDEPENDENCE": (
                "Find a source family independent of existing evidence that "
                f'evaluates: "{statement}"',
                "Increase source-family diversity",
                ("REGULATORY_FILING", "INDEPENDENT_NEWS"),
            ),
        }
        for reason in reasons:
            template = templates.get(reason, templates["UNSUPPORTED"])
            query = FollowUpQuery(
                claim_id=gap.claim_id,
                query=template[0],
                intent=template[1],
                loop_index=loop_index,
                preferred_source_types=template[2],
            )
            if query.query not in {item.query for item in queries}:
                queries.append(query)
            if len(queries) >= self.max_queries:
                break
        return tuple(queries)


class FollowUpLoop:
    """Run at most ``max_loops`` targeted evidence passes."""

    def __init__(self, planner: EvidenceGapPlanner | None = None, *, max_loops: int = 3) -> None:
        if max_loops < 0:
            raise ValueError("max_loops cannot be negative")
        self.planner = planner or EvidenceGapPlanner()
        self.max_loops = max_loops

    def run(
        self,
        gap: EvidenceGap | Mapping[str, Any] | None = None,
        retrieve: Callable[
            [FollowUpQuery], Sequence[EvidenceReference | Mapping[str, Any] | UUID | str]
        ] | None = None,
        *,
        verify: Callable[..., Any] | None = None,
        reserve: Callable[[int], Any] | None = None,
        claim_id: UUID | str | None = None,
        gaps: Sequence[str] | None = None,
        results: Sequence[Mapping[str, Any]] | None = None,
    ) -> FollowUpResult:
        # The compact replay contract is useful for workers that already
        # persisted provider results. It applies the same stopping semantics
        # without inventing a second claim or evidence record.
        if claim_id is not None or gaps is not None or results is not None:
            if claim_id is None:
                raise ValueError("claim_id is required for persisted follow-up results")
            return self._run_persisted_results(claim_id, gaps or (), results or ())
        if gap is None or retrieve is None:
            raise ValueError("gap and retrieve are required")
        current = gap if isinstance(gap, EvidenceGap) else EvidenceGap.model_validate(gap)
        lineage = list(current.evidence)
        if current.sufficient:
            return FollowUpResult(
                claim_id=current.claim_id,
                stop_reason=FollowUpStopReason.SUFFICIENT,
                evidence_lineage=tuple(lineage),
                partial=False,
            )
        if current.provider_degraded:
            return self._result(current, FollowUpStopReason.PROVIDER_DEGRADED, (), lineage)
        if self.max_loops == 0:
            return self._result(current, FollowUpStopReason.LOOP_BUDGET, (), lineage)

        iterations: list[FollowUpIteration] = []
        for loop_index in range(1, self.max_loops + 1):
            if reserve is not None and not _reserve_allowed(reserve, loop_index):
                return self._result(
                    current, FollowUpStopReason.BUDGET_EXCEEDED, iterations, lineage
                )
            queries = self.planner.plan(current, loop_index=loop_index)
            if not queries:
                return self._result(current, FollowUpStopReason.NO_PROGRESS, iterations, lineage)
            before = _lineage_fingerprint(lineage)
            added: list[EvidenceReference] = []
            try:
                for query in queries:
                    result = retrieve(query)
                    if _provider_degraded(result):
                        return self._result(
                            current,
                            FollowUpStopReason.PROVIDER_DEGRADED,
                            iterations,
                            lineage,
                        )
                    for item in result or ():
                        reference = _evidence_reference(item, current.claim_id)
                        if reference.evidence_id not in {entry.evidence_id for entry in lineage}:
                            lineage.append(reference)
                            added.append(reference)
            except ProviderDegradedError:
                return self._result(
                    current, FollowUpStopReason.PROVIDER_DEGRADED, iterations, lineage
                )

            progress = _lineage_fingerprint(lineage) != before
            resolved = _verification_sufficient(verify, current, tuple(lineage))
            stop_reason = FollowUpStopReason.SUFFICIENT if resolved else (
                None if progress else FollowUpStopReason.NO_PROGRESS
            )
            iterations.append(
                FollowUpIteration(
                    loop_index=loop_index,
                    queries=queries,
                    added_evidence_ids=tuple(item.evidence_id for item in added),
                    lineage_size=len(lineage),
                    progress=progress,
                    stop_reason=stop_reason,
                )
            )
            if resolved:
                return self._result(
                    current,
                    FollowUpStopReason.SUFFICIENT,
                    iterations,
                    lineage,
                    partial=False,
                )
            if not progress:
                return self._result(current, FollowUpStopReason.NO_PROGRESS, iterations, lineage)

        return self._result(current, FollowUpStopReason.LOOP_BUDGET, iterations, lineage)

    def _run_persisted_results(
        self,
        claim_id: UUID | str,
        gaps: Sequence[str],
        results: Sequence[Mapping[str, Any]],
    ) -> FollowUpResult:
        lineage: list[EvidenceReference] = []
        for result in results:
            for prior in result.get("prior_lineage", ()) or ():
                reference = EvidenceReference(evidence_id=str(prior), claim_id=claim_id)
                if reference.evidence_id not in {item.evidence_id for item in lineage}:
                    lineage.append(reference)
        iterations: list[FollowUpIteration] = []
        for loop_index, result in enumerate(results[: self.max_loops], start=1):
            queries = tuple(
                FollowUpQuery(
                    claim_id=claim_id,
                    query=str(gap or "Find independent evidence for this claim"),
                    intent="Target evidence gap",
                    loop_index=loop_index,
                )
                for gap in (gaps or ("UNSUPPORTED",))
            )
            status = str(result.get("provider_status", "")).upper()
            if status in {"TEMPORARY_FAILURE", "RATE_LIMITED", "TIMEOUT", "DEGRADED"}:
                iterations.append(
                    FollowUpIteration(
                        loop_index=loop_index,
                        queries=queries,
                        lineage_size=len(lineage),
                        progress=False,
                        stop_reason=FollowUpStopReason.PROVIDER_DEGRADED,
                    )
                )
                return self._result(
                    EvidenceGap(claim_id=claim_id),
                    FollowUpStopReason.PROVIDER_DEGRADED,
                    iterations,
                    lineage,
                )
            progress = bool(result.get("new_evidence"))
            if progress:
                evidence_id = result.get("lineage_id", f"evidence-{loop_index}")
                reference = EvidenceReference(evidence_id=evidence_id, claim_id=claim_id)
                if reference.evidence_id not in {item.evidence_id for item in lineage}:
                    lineage.append(reference)
            exhausted_results = loop_index >= len(results)
            stop_reason = (
                FollowUpStopReason.SUFFICIENT
                if progress and exhausted_results
                else FollowUpStopReason.NO_PROGRESS
                if not progress
                else None
            )
            iterations.append(
                FollowUpIteration(
                    loop_index=loop_index,
                    queries=queries,
                    added_evidence_ids=(lineage[-1].evidence_id,) if progress else (),
                    lineage_size=len(lineage),
                    progress=progress,
                    stop_reason=stop_reason,
                )
            )
            if progress and exhausted_results:
                return self._result(
                    EvidenceGap(claim_id=claim_id),
                    FollowUpStopReason.SUFFICIENT,
                    iterations,
                    lineage,
                    partial=False,
                )
            return self._result(
                EvidenceGap(claim_id=claim_id),
                FollowUpStopReason.NO_PROGRESS,
                iterations,
                lineage,
            )
        return self._result(
            EvidenceGap(claim_id=claim_id),
            FollowUpStopReason.LOOP_BUDGET_EXCEEDED,
            iterations,
            lineage,
        )

    def _result(
        self,
        gap: EvidenceGap,
        reason: FollowUpStopReason,
        iterations: Sequence[FollowUpIteration],
        lineage: Sequence[EvidenceReference],
        *,
        partial: bool = True,
    ) -> FollowUpResult:
        return FollowUpResult(
            claim_id=gap.claim_id,
            stop_reason=reason,
            iterations=tuple(iterations),
            evidence_lineage=tuple(lineage),
            partial=partial,
        )


def run_follow_up(
    gap: EvidenceGap | Mapping[str, Any],
    retrieve: Callable[
        [FollowUpQuery], Sequence[EvidenceReference | Mapping[str, Any] | UUID | str]
    ],
    *,
    verify: Callable[..., Any] | None = None,
    max_loops: int = 3,
    reserve: Callable[[int], Any] | None = None,
) -> FollowUpResult:
    return FollowUpLoop(max_loops=max_loops).run(gap, retrieve, verify=verify, reserve=reserve)


def build_evidence_gap(
    claim_id: UUID | str,
    assessment: Mapping[str, Any],
    *,
    claim_statement: str = "",
    materiality: str = "MEDIUM",
    evidence: Sequence[EvidenceReference] = (),
) -> EvidenceGap:
    """Normalize verifier gaps into planner input without changing claims."""

    reasons: list[str] = []
    if assessment.get("unsupported") or assessment.get("outcome") in {"FAIL", "INSUFFICIENT"}:
        reasons.append("UNSUPPORTED")
    if assessment.get("partial") or assessment.get("outcome") == "PARTIAL":
        reasons.append("PARTIAL")
    if assessment.get("high_authority_conflict"):
        reasons.append("HIGH_AUTHORITY_CONFLICT")
    if assessment.get("numeric_failure"):
        reasons.append("NUMERIC_FAILURE")
    if assessment.get("period_failure"):
        reasons.append("PERIOD_FAILURE")
    if assessment.get("low_independence"):
        reasons.append("LOW_INDEPENDENCE")
    return EvidenceGap(
        claim_id=claim_id,
        claim_statement=claim_statement,
        materiality=materiality,
        reasons=tuple(reasons),
        evidence=tuple(evidence),
        source_family_count=int(assessment.get("source_family_count", 0)),
        sufficient=bool(assessment.get("sufficient", False)),
        provider_degraded=bool(assessment.get("provider_degraded", False)),
    )


BoundedFollowUpLoop = FollowUpLoop
follow_up_loop = run_follow_up


def _evidence_reference(
    value: EvidenceReference | Mapping[str, Any] | UUID | str,
    claim_id: UUID | str,
) -> EvidenceReference:
    if isinstance(value, EvidenceReference):
        return value
    if isinstance(value, Mapping):
        payload = dict(value)
        payload.setdefault("claim_id", claim_id)
        if "evidence_id" not in payload:
            payload["evidence_id"] = payload.get("id")
        return EvidenceReference.model_validate(payload)
    return EvidenceReference(evidence_id=value, claim_id=claim_id)


def _lineage_fingerprint(lineage: Sequence[EvidenceReference]) -> str:
    values = sorted(str(item.evidence_id) for item in lineage)
    return hashlib.sha256(json.dumps(values).encode("utf-8")).hexdigest()


def _provider_degraded(value: Any) -> bool:
    if isinstance(value, Mapping):
        return bool(value.get("provider_degraded")) or str(value.get("status", "")).upper() in {
            "PROVIDER_DEGRADED",
            "DEGRADED",
            "TEMPORARY_FAILURE",
            "RATE_LIMITED",
            "TIMEOUT",
        }
    return bool(getattr(value, "provider_degraded", False)) or str(
        getattr(value, "status", "")
    ).upper() in {
        "PROVIDER_DEGRADED",
        "DEGRADED",
        "TEMPORARY_FAILURE",
        "RATE_LIMITED",
        "TIMEOUT",
    }


def _verification_sufficient(
    verify: Callable[..., Any] | None,
    gap: EvidenceGap,
    lineage: Sequence[EvidenceReference],
) -> bool:
    if verify is None:
        return False
    parameters = inspect.signature(verify).parameters
    value = verify(tuple(lineage)) if len(parameters) == 1 else verify(gap, tuple(lineage))
    if isinstance(value, Mapping):
        return bool(value.get("sufficient") or value.get("resolved"))
    return bool(value)


def _reserve_allowed(reserve: Callable[[int], Any], loop_index: int) -> bool:
    value = reserve(loop_index)
    if isinstance(value, Mapping):
        return bool(value.get("allowed", False))
    return bool(getattr(value, "allowed", value))


__all__ = [
    "BoundedFollowUpLoop",
    "EvidenceGap",
    "EvidenceGapPlanner",
    "EvidenceReference",
    "FollowUpIteration",
    "FollowUpLoop",
    "FollowUpQuery",
    "FollowUpResult",
    "FollowUpStopReason",
    "ProviderDegradedError",
    "build_evidence_gap",
    "follow_up_loop",
    "run_follow_up",
]
