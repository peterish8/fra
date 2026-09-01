"""Fixture-driven official and commercial financial adapters.

Adapters accept payloads supplied by an integration boundary.  They never
perform network access themselves, so production transport, credentials, and
licensing remain explicit infrastructure decisions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.providers.contracts import ProviderStatus

from .contracts import FinancialProviderResult, normalize_financial_result


class FixtureFinancialAdapter:
    official = False

    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        provider: str,
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
    ) -> None:
        self.payload = payload
        self.provider = provider
        self.status = ProviderStatus(status)

    def fetch(self, query: Mapping[str, str]) -> FinancialProviderResult:
        del query
        return normalize_financial_result(
            provider=self.provider,
            payload=self.payload,
            official=self.official,
            provider_status=self.status,
            source_type="REGULATORY_FILING" if self.official else "FINANCIAL_API",
        )


class OfficialFilingAdapter(FixtureFinancialAdapter):
    official = True

    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        provider: str = "OFFICIAL_FILING",
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
    ) -> None:
        super().__init__(payload, provider=provider, status=status)


class EodhdAdapter(FixtureFinancialAdapter):
    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
    ) -> None:
        super().__init__(payload, provider="EODHD", status=status)


class TwelveDataAdapter(FixtureFinancialAdapter):
    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
    ) -> None:
        super().__init__(payload, provider="TWELVE_DATA", status=status)


class FinancialProviderRouter:
    """Official-first routing with replaceable fallback providers."""

    def __init__(
        self,
        official: FixtureFinancialAdapter | None,
        fallbacks: Sequence[FixtureFinancialAdapter] = (),
    ) -> None:
        self.official = official
        self.fallbacks = tuple(fallbacks)

    def fetch(self, query: Mapping[str, str]) -> FinancialProviderResult:
        providers = ((self.official,) if self.official is not None else ()) + self.fallbacks
        last: FinancialProviderResult | None = None
        for index, provider in enumerate(providers):
            result = provider.fetch(query)
            if result.status is ProviderStatus.SUCCESS:
                # A filing remains the selected observation.  A configured
                # commercial provider can still be a cross-check; never
                # replace or average an official value when it differs.
                if index == 0 and self.official is not None:
                    cross_checks = [fallback.fetch(query) for fallback in self.fallbacks]
                    successful_checks = [
                        candidate
                        for candidate in cross_checks
                        if candidate.status is ProviderStatus.SUCCESS
                    ]
                    if any(_facts_disagree(result, candidate) for candidate in successful_checks):
                        metadata = dict(result.safe_metadata)
                        metadata["disagreement"] = True
                        metadata["cross_check_providers"] = [
                            candidate.provider for candidate in successful_checks
                        ]
                        return result.model_copy(update={"safe_metadata": metadata})
                return result
            last = result
            if result.status in {
                ProviderStatus.ACCESS_RESTRICTED,
                ProviderStatus.PERMANENT_FAILURE,
            }:
                continue
        return last or FinancialProviderResult(
            provider="FINANCIAL_ROUTER",
            status=ProviderStatus.NO_RESULTS,
            reason="No financial provider was configured.",
        )

    retrieve = fetch


def route_financial_facts(
    query: Mapping[str, str],
    *,
    official: FixtureFinancialAdapter | None,
    fallbacks: Sequence[FixtureFinancialAdapter] = (),
) -> FinancialProviderResult:
    return FinancialProviderRouter(official, fallbacks).fetch(query)


def _facts_disagree(primary: FinancialProviderResult, cross_check: FinancialProviderResult) -> bool:
    """Compare like-for-like facts without normalizing away a disagreement."""

    for left in primary.facts:
        for right in cross_check.facts:
            if (
                left.metric == right.metric
                and left.currency == right.currency
                and left.normalized_value != right.normalized_value
            ):
                return True
    return False


__all__ = [
    "EodhdAdapter",
    "FinancialProviderRouter",
    "FixtureFinancialAdapter",
    "OfficialFilingAdapter",
    "TwelveDataAdapter",
    "route_financial_facts",
]
