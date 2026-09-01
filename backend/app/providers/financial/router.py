"""Official-first financial routing facade and fixture contract adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .adapters import FixtureFinancialAdapter
from .contracts import FinancialProviderResult


class FinancialRouter:
    """Route injected adapters, preferring the official filing adapter."""

    def __init__(
        self,
        official: FixtureFinancialAdapter | None = None,
        fallbacks: Sequence[FixtureFinancialAdapter] = (),
    ) -> None:
        self.official = official
        self.fallbacks = tuple(fallbacks)

    def fetch(self, query: Mapping[str, str]) -> FinancialProviderResult:
        from .adapters import FinancialProviderRouter

        return FinancialProviderRouter(self.official, self.fallbacks).fetch(query)

    retrieve = fetch


FinancialProviderRouterFacade = FinancialRouter
route_financial = FinancialRouter


__all__ = ["FinancialRouter", "FinancialProviderRouterFacade", "route_financial"]
