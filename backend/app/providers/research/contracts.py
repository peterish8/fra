"""Provider-neutral contracts for optional deep research."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.providers.contracts import ProviderStatus, normalize_provider_result


class ResearchDepth(StrEnum):
    STANDARD = "STANDARD"
    DEEP = "DEEP"


class DeepResearchRequest(BaseModel):
    """Explicit routing context; no provider-specific fields are exposed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str = Field(min_length=1, max_length=8_000)
    depth: ResearchDepth = ResearchDepth.STANDARD
    materiality: str = Field(default="MEDIUM", min_length=1, max_length=20)
    unresolved: bool = False
    complex_risk: bool = False
    watchlist_finalist: bool = False
    max_sources: int = Field(default=20, ge=1, le=100)
    max_cost_usd: Decimal = Field(default=Decimal("5"), ge=0)
    claim_id: str | None = Field(default=None, max_length=200)
    research_run_id: str | None = Field(default=None, max_length=200)

    @field_validator("query", "materiality", "claim_id", "research_run_id", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> Any:
        if value is None:
            return value
        return value.strip() if isinstance(value, str) else value


class DeepResearchEvidence(BaseModel):
    """A retrieval/reasoning item, never an authoritative claim verdict."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str | None = None
    url: str | None = None
    title: str | None = None
    excerpt: str | None = None
    source_type: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeepResearchResult(BaseModel):
    """Normalized deep output with an explicit non-authoritative boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1)
    operation: str = "deep_research"
    model: str = Field(min_length=1)
    prompt_version: str = "deep-research-v1"
    status: ProviderStatus | str
    data: dict[str, Any] | None = None
    evidence: list[DeepResearchEvidence] = Field(default_factory=list)
    provider_request_id: str | None = None
    retrieved_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    latency_ms: float = Field(default=0, ge=0)
    cost_usd_estimate: Decimal = Field(default=Decimal("0"), ge=0)
    safe_metadata: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    retry_classification: str = "NOT_RETRYABLE"
    authoritative: bool = False
    verdict: None = None
    final_truth: bool = False
    eligible: bool = False
    invoke: bool = False
    route_reason: str | None = None

    @classmethod
    def skipped(cls, *, reason: str, model: str = "not-invoked") -> DeepResearchResult:
        return cls(
            provider="deep-research",
            model=model,
            status="SKIPPED",
            safe_metadata={"route": "STANDARD", "reason": reason, "authoritative": False},
            prompt_version="deep-research-v1",
            eligible=False,
            invoke=False,
        )


class DeepResearchCapability(Protocol):
    provider: str
    model: str

    def research(self, request: DeepResearchRequest) -> DeepResearchResult:
        """Run selected deep research and return non-authoritative evidence."""


def normalize_deep_result(
    *,
    provider: str,
    model: str,
    payload: Mapping[str, Any] | None,
    provider_status: ProviderStatus | str,
    provider_request_id: str | None = None,
    retrieved_at: str | datetime | None = None,
    latency_ms: int | float | Decimal = 0,
    cost_usd_estimate: Decimal | int | float | str | None = None,
    raw_metadata: Mapping[str, Any] | None = None,
    error_code: str | None = None,
    retry_classification: str = "NOT_RETRYABLE",
    prompt_version: str = "deep-research-v1",
) -> DeepResearchResult:
    """Normalize fixture/provider output and keep final truth out of it."""

    status_payload = payload
    if status_payload is None and str(provider_status).upper() == ProviderStatus.SUCCESS.value:
        status_payload = {}
    base = normalize_provider_result(
        provider=provider,
        operation="deep_research",
        payload=status_payload,
        provider_status=provider_status,
        provider_request_id=provider_request_id,
        retrieved_at=retrieved_at or datetime.now(UTC),
        latency_ms=latency_ms,
        cost_usd_estimate=cost_usd_estimate,
        raw_metadata=raw_metadata,
        error_code=error_code,
        retry_classification=retry_classification,
    )
    status = base.status
    if status is ProviderStatus.SUCCESS and payload is not None:
        data = _safe_research_data(payload)
        evidence = _evidence_from_payload(payload.get("evidence", []))
    else:
        data, evidence = None, []
    metadata = dict(base.safe_metadata)
    metadata.update({"model": model, "authoritative": False})
    return DeepResearchResult(
        provider=base.provider,
        model=model,
        prompt_version=prompt_version,
        status=status,
        data=data,
        evidence=evidence,
        provider_request_id=base.provider_request_id,
        retrieved_at=base.retrieved_at,
        latency_ms=base.latency_ms,
        cost_usd_estimate=base.cost_usd_estimate,
        safe_metadata=metadata,
        error_code=base.error_code,
        retry_classification=base.retry_classification,
        authoritative=False,
        verdict=None,
        final_truth=False,
    )


def _safe_research_data(value: Mapping[str, Any]) -> dict[str, Any]:
    forbidden = {"verdict", "final_verdict", "claim_verdict", "authoritative_truth"}
    return {
        str(key): _safe_value(item)
        for key, item in value.items()
        if str(key).casefold() not in forbidden
    }


def _safe_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _safe_research_data(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _evidence_from_payload(value: Any) -> list[DeepResearchEvidence]:
    if not isinstance(value, list):
        return []
    result: list[DeepResearchEvidence] = []
    for item in value:
        if isinstance(item, Mapping):
            try:
                result.append(DeepResearchEvidence.model_validate(item))
            except ValueError:
                continue
    return result


__all__ = [
    "DeepResearchCapability",
    "DeepResearchEvidence",
    "DeepResearchRequest",
    "DeepResearchResult",
    "ResearchDepth",
    "normalize_deep_result",
]
