"""Fixture-only deep research adapter used for contract and routing tests."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.providers.contracts import ProviderStatus

from .contracts import (
    DeepResearchRequest,
    DeepResearchResult,
    ResearchDepth,
    normalize_deep_result,
)


class FixtureDeepResearchAdapter:
    """Return supplied evidence without opening a network connection."""

    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        provider: str = "FIXTURE_DEEP_RESEARCH",
        model: str = "fixture-deep-v1",
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
        cost_usd_estimate: Decimal | int | float | str = Decimal("0"),
        latency_ms: int | float = 0,
        provider_request_id: str | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.payload = dict(payload or {})
        self.status = status
        self.cost_usd_estimate = cost_usd_estimate
        self.latency_ms = latency_ms
        self.provider_request_id = provider_request_id
        self.calls: list[DeepResearchRequest] = []

    def research(self, request: DeepResearchRequest | Mapping[str, Any]) -> DeepResearchResult:
        if isinstance(request, DeepResearchRequest):
            normalized_request = request
            payload = self.payload
        else:
            payload = dict(request) if not self.payload else self.payload
            normalized_request = DeepResearchRequest(
                query=str(request.get("query") or "fixture deep research"),
                depth=ResearchDepth.DEEP,
                materiality=str(request.get("materiality") or "HIGH"),
            )
        self.calls.append(normalized_request)
        return normalize_deep_result(
            provider=self.provider,
            model=self.model,
            payload=payload,
            provider_status=self.status,
            provider_request_id=self.provider_request_id,
            latency_ms=self.latency_ms,
            cost_usd_estimate=self.cost_usd_estimate,
            raw_metadata={"fixture": True, "request_claim_id": normalized_request.claim_id},
            retry_classification=(
                "RETRYABLE"
                if str(self.status).upper()
                in {ProviderStatus.TIMEOUT.value, ProviderStatus.RATE_LIMITED.value,
                    ProviderStatus.TEMPORARY_FAILURE.value}
                else "NOT_RETRYABLE"
            ),
        )

    run = research
    execute = research


FixtureDeepResearchProvider = FixtureDeepResearchAdapter
DeepResearchAdapter = FixtureDeepResearchAdapter


__all__ = [
    "DeepResearchAdapter",
    "FixtureDeepResearchAdapter",
    "FixtureDeepResearchProvider",
]
