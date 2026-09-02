"""Fixture-backed, provider-neutral deep research lane."""

from .contracts import (
    DeepResearchCapability,
    DeepResearchEvidence,
    DeepResearchRequest,
    DeepResearchResult,
    ResearchDepth,
    normalize_deep_result,
)
from .fixture import (
    DeepResearchAdapter,
    FixtureDeepResearchAdapter,
    FixtureDeepResearchProvider,
)
from .router import (
    DeepResearchProviderRouter,
    DeepResearchRouter,
    DeepResearchRouting,
    DeepResearchRoutingDecision,
    DeepResearchRoutingPolicy,
    route_deep_research,
    should_route_deep_research,
    should_use_deep_research,
)

__all__ = [
    "DeepResearchAdapter",
    "DeepResearchCapability",
    "DeepResearchEvidence",
    "DeepResearchProviderRouter",
    "DeepResearchRequest",
    "DeepResearchResult",
    "DeepResearchRouter",
    "DeepResearchRouting",
    "DeepResearchRoutingDecision",
    "DeepResearchRoutingPolicy",
    "FixtureDeepResearchAdapter",
    "FixtureDeepResearchProvider",
    "ResearchDepth",
    "normalize_deep_result",
    "route_deep_research",
    "should_route_deep_research",
    "should_use_deep_research",
]
