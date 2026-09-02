"""Cost-aware routing for optional deep research."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Protocol

from .contracts import DeepResearchRequest, DeepResearchResult, ResearchDepth
from .fixture import FixtureDeepResearchAdapter


class DeepResearchProvider(Protocol):
    provider: str
    model: str

    def research(self, request: DeepResearchRequest) -> DeepResearchResult: ...


class DeepResearchRoutingDecision(DeepResearchResult):
    """Result envelope that exposes why a costly lane was or was not used."""

    route: bool = False
    route_reason: str | None = None


class DeepResearchRoutingPolicy:
    """Pure policy for selecting deep research work."""

    def decide(self, request: DeepResearchRequest) -> tuple[bool, str]:
        if request.depth is ResearchDepth.DEEP:
            return True, "user_selected_deep"
        materiality = request.materiality.strip().upper()
        if request.watchlist_finalist:
            return True, "watchlist_finalist"
        if request.complex_risk:
            return True, "complex_risk"
        if request.unresolved and materiality in {"HIGH", "CRITICAL"}:
            return True, "unresolved_high_materiality"
        return False, "standard_or_low_materiality"

    def should_route(self, request: DeepResearchRequest) -> bool:
        return self.decide(request)[0]


class DeepResearchRouter:
    """Invoke an injected deep adapter only when policy permits it."""

    def __init__(
        self,
        adapter: DeepResearchProvider | None = None,
        *,
        policy: DeepResearchRoutingPolicy | None = None,
    ) -> None:
        self.adapter = adapter or FixtureDeepResearchAdapter()
        self.policy = policy or DeepResearchRoutingPolicy()

    def route(self, request: DeepResearchRequest | Mapping[str, Any]) -> DeepResearchResult:
        normalized = _coerce_request(request)
        should_route, reason = self.policy.decide(normalized)
        if not should_route:
            return DeepResearchResult.skipped(reason=reason).model_copy(
                update={"eligible": False, "invoke": False, "route_reason": reason}
            )

        estimated = _estimated_cost(self.adapter)
        if estimated is not None and estimated > normalized.max_cost_usd:
            return DeepResearchResult(
                provider=getattr(self.adapter, "provider", "deep-research"),
                model=getattr(self.adapter, "model", "unknown"),
                status="COST_BUDGET_EXCEEDED",
                error_code="COST_BUDGET_EXCEEDED",
                safe_metadata={
                    "route": reason,
                    "estimated_cost_usd": str(estimated),
                    "max_cost_usd": str(normalized.max_cost_usd),
                    "authoritative": False,
                },
                eligible=True,
                invoke=False,
                route_reason=reason,
            )
        result = self.adapter.research(normalized)
        # Even an injected adapter cannot elevate this retrieval lane to truth.
        return result.model_copy(
            update={
                "authoritative": False,
                "verdict": None,
                "safe_metadata": {
                    **result.safe_metadata,
                    "route": reason,
                    "authoritative": False,
                },
                "eligible": True,
                "invoke": True,
                "route_reason": reason,
            }
        )

    research = route
    run = route


def should_use_deep_research(
    request: DeepResearchRequest | Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> bool:
    if request is None:
        request = kwargs
    return DeepResearchRoutingPolicy().should_route(_coerce_request(request))


def should_route_deep_research(
    request: DeepResearchRequest | Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> bool:
    return should_use_deep_research(request, **kwargs)


def route_deep_research(
    request: DeepResearchRequest | Mapping[str, Any],
    adapter: DeepResearchProvider,
    *,
    policy: DeepResearchRoutingPolicy | None = None,
) -> DeepResearchResult:
    return DeepResearchRouter(adapter, policy=policy).route(request)


def _coerce_request(value: DeepResearchRequest | Mapping[str, Any]) -> DeepResearchRequest:
    if isinstance(value, DeepResearchRequest):
        return value
    payload = dict(value)
    if "depth" not in payload and "mode" in payload:
        payload["depth"] = payload.pop("mode")
    if "watchlist_finalist" not in payload and "finalist" in payload:
        payload["watchlist_finalist"] = payload.pop("finalist")
    return DeepResearchRequest.model_validate(payload)


def _estimated_cost(adapter: object) -> Decimal | None:
    value = getattr(adapter, "estimated_cost_usd", None)
    if value is None:
        value = getattr(adapter, "cost_usd_estimate", None)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return None


DeepResearchRouting = DeepResearchRouter
DeepResearchProviderRouter = DeepResearchRouter


__all__ = [
    "DeepResearchProvider",
    "DeepResearchProviderRouter",
    "DeepResearchRouter",
    "DeepResearchRouting",
    "DeepResearchRoutingDecision",
    "DeepResearchRoutingPolicy",
    "route_deep_research",
    "should_route_deep_research",
    "should_use_deep_research",
]
