"""Configurable evidence freshness and affected-claim selection."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FreshnessState(StrEnum):
    CURRENT = "CURRENT"
    AGING = "AGING"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class FreshnessThreshold(BaseModel):
    """Age boundaries in days for one claim type."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    aging_after_days: int = Field(ge=0)
    stale_after_days: int = Field(ge=0)
    invalidate_after_days: int | None = Field(default=None, ge=0)

    def model_post_init(self, __context: Any) -> None:
        if self.stale_after_days < self.aging_after_days:
            raise ValueError("stale_after_days must be at least aging_after_days")
        if (
            self.invalidate_after_days is not None
            and self.invalidate_after_days < self.stale_after_days
        ):
            raise ValueError("invalidate_after_days must be at least stale_after_days")


class FreshnessPolicy(BaseModel):
    """Versioned claim-type policy; unknown types use ``default``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(default="freshness-v1", min_length=1, max_length=80)
    default: FreshnessThreshold = Field(
        default_factory=lambda: FreshnessThreshold(
            aging_after_days=90,
            stale_after_days=365,
            invalidate_after_days=None,
        )
    )
    by_claim_type: dict[str, FreshnessThreshold] = Field(default_factory=dict)

    @field_validator("by_claim_type", mode="before")
    @classmethod
    def normalize_claim_types(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return {_claim_type_key(key): threshold for key, threshold in value.items()}

    def threshold_for(self, claim_type: str | None) -> FreshnessThreshold:
        key = _claim_type_key(claim_type)
        return self.by_claim_type.get(key, self.default)

    def classify(
        self,
        *,
        claim_type: str,
        observed_at: datetime | date | str,
        now: datetime | date | str | None = None,
        invalidated: bool = False,
    ) -> FreshnessEvaluation:
        return evaluate_freshness(
            claim_type,
            observed_at,
            evaluated_at=now,
            policy=self,
            invalidated=invalidated,
        )

    def target_stale_claims(
        self,
        claims: Iterable[Mapping[str, Any] | Any],
        *,
        now: datetime | date | str | None = None,
    ) -> list[dict[str, Any]]:
        """Return refresh targets while retaining each claim's old history."""

        targets: list[dict[str, Any]] = []
        for claim in claims:
            payload = dict(_as_mapping(claim))
            observed_at = payload.get(
                "observed_at",
                payload.get(
                    "retrieved_at",
                    payload.get("last_verified_at", payload.get("created_at")),
                ),
            )
            claim_id = payload.get("claim_id", payload.get("id"))
            if observed_at is None or claim_id is None:
                continue
            result = self.classify(
                claim_type=str(payload.get("claim_type", payload.get("category", "default"))),
                observed_at=observed_at,
                now=now,
                invalidated=bool(payload.get("invalidated", False)),
            )
            if result.affected:
                payload["freshness"] = result.state.value
                payload["freshness_reason"] = result.reason
                targets.append(payload)
        return targets


class FreshnessEvaluation(BaseModel):
    """Deterministic freshness result while retaining the retrieval date."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: FreshnessState
    claim_type: str
    retrieved_at: datetime
    evaluated_at: datetime
    age_days: int = Field(ge=0)
    reason: str
    policy_version: str

    @property
    def affected(self) -> bool:
        return self.state in {FreshnessState.STALE, FreshnessState.INVALIDATED}


class AffectedClaim(BaseModel):
    """Claim selected for revalidation, with its new freshness state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: UUID | str
    state: FreshnessState
    claim_type: str
    age_days: int = Field(ge=0)
    reason: str


def evaluate_freshness(
    claim_type: str | None,
    retrieved_at: datetime | date | str,
    *,
    evaluated_at: datetime | date | str | None = None,
    policy: FreshnessPolicy | None = None,
    invalidated: bool = False,
) -> FreshnessEvaluation:
    """Evaluate evidence age without modifying its historical record."""

    active_policy = policy or FreshnessPolicy()
    retrieved = _as_datetime(retrieved_at)
    evaluated = _as_datetime(evaluated_at) if evaluated_at is not None else datetime.now(UTC)
    if evaluated < retrieved:
        raise ValueError("evaluated_at cannot precede retrieved_at")
    age_days = (evaluated.date() - retrieved.date()).days
    threshold = active_policy.threshold_for(claim_type)
    normalized_type = _claim_type_key(claim_type) or "default"
    if invalidated or (
        threshold.invalidate_after_days is not None
        and age_days > threshold.invalidate_after_days
    ):
        state = FreshnessState.INVALIDATED
        reason = "Evidence exceeded the invalidation window or was superseded."
    elif age_days > threshold.stale_after_days:
        state = FreshnessState.STALE
        reason = "Evidence exceeded the stale window and needs revalidation."
    elif age_days > threshold.aging_after_days:
        state = FreshnessState.AGING
        reason = "Evidence is aging and should be monitored."
    else:
        state = FreshnessState.CURRENT
        reason = "Evidence is within the configured current window."
    return FreshnessEvaluation(
        state=state,
        claim_type=normalized_type,
        retrieved_at=retrieved,
        evaluated_at=evaluated,
        age_days=age_days,
        reason=reason,
        policy_version=active_policy.version,
    )


def select_affected_claims(
    claims: Iterable[Mapping[str, Any] | Any],
    *,
    evaluated_at: datetime | date | str | None = None,
    policy: FreshnessPolicy | None = None,
) -> list[AffectedClaim]:
    """Select stale/invalidated claims without dropping current history."""

    affected: list[AffectedClaim] = []
    for claim in claims:
        payload = _as_mapping(claim)
        claim_id = payload.get("claim_id", payload.get("id"))
        retrieved_at = payload.get(
            "retrieved_at",
            payload.get("last_verified_at", payload.get("created_at")),
        )
        if claim_id is None or retrieved_at is None:
            continue
        claim_type = str(payload.get("claim_type", payload.get("category", "default")))
        result = evaluate_freshness(
            claim_type,
            retrieved_at,
            evaluated_at=evaluated_at,
            policy=policy,
            invalidated=bool(payload.get("invalidated", False)),
        )
        if result.affected:
            affected.append(
                AffectedClaim(
                    claim_id=claim_id,
                    state=result.state,
                    claim_type=result.claim_type,
                    age_days=result.age_days,
                    reason=result.reason,
                )
            )
    return affected


def advance_freshness(
    previous: FreshnessState | str,
    evaluation: FreshnessState | str,
) -> FreshnessState:
    """Apply a monotonic historical transition to an existing record.

    Revalidation creates a new claim/evidence version; it must not rewrite the
    prior stale record. This helper is for evaluating an existing version's
    state, so a later state cannot silently move backward.
    """

    states = list(FreshnessState)
    prior = FreshnessState(previous)
    current = FreshnessState(evaluation)
    return states[max(states.index(prior), states.index(current))]


affected_claims = select_affected_claims
classify_freshness = evaluate_freshness


def _claim_type_key(value: str | None) -> str:
    if not value:
        return ""
    return "_".join(value.strip().casefold().replace("-", " ").split())


def _as_datetime(value: datetime | date | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_mapping(value: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        result = dump()
        if isinstance(result, Mapping):
            return result
    raise TypeError("claim must be a mapping or a model with model_dump")


__all__ = [
    "AffectedClaim",
    "FreshnessEvaluation",
    "FreshnessPolicy",
    "FreshnessState",
    "FreshnessThreshold",
    "affected_claims",
    "advance_freshness",
    "classify_freshness",
    "evaluate_freshness",
    "select_affected_claims",
]
