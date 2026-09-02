"""Fixture adapter façade used by the provider contract tests."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.providers.contracts import ProviderStatus

from .contracts import DeepResearchRequest, DeepResearchResult, normalize_deep_result


class DeepResearchAdapter:
    """Provider-neutral normalizer; it performs no live provider calls."""

    def __init__(
        self,
        *,
        provider: str = "FIXTURE_DEEP_RESEARCH",
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
        cost_usd_estimate: Decimal | int | float | str = Decimal("0"),
    ) -> None:
        self.provider = provider
        self.status = status
        self.cost_usd_estimate = cost_usd_estimate

    def normalize(
        self,
        payload: Mapping[str, Any] | None,
        *,
        prompt_version: str = "deep-research-v1",
        model: str = "fixture-deep-v1",
        provider_request_id: str | None = None,
    ) -> DeepResearchResult:
        return normalize_deep_result(
            provider=self.provider,
            model=model,
            payload=payload,
            provider_status=self.status,
            provider_request_id=provider_request_id,
            cost_usd_estimate=self.cost_usd_estimate,
            prompt_version=prompt_version,
        )

    def research(self, request: DeepResearchRequest) -> DeepResearchResult:
        del request
        return self.normalize({}, model="fixture-deep-v1")


__all__ = ["DeepResearchAdapter"]
