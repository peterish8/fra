"""Official-first, provider-neutral financial adapters."""

from .adapters import (
    EodhdAdapter,
    FinancialProviderRouter,
    FixtureFinancialAdapter,
    OfficialFilingAdapter,
    SECCompanyFactsHttpAdapter,
    TwelveDataAdapter,
    route_financial_facts,
)
from .contracts import (
    FinancialFact,
    FinancialProvider,
    FinancialProviderResult,
    ProviderStatus,
    normalize_financial_result,
)
from .router import FinancialRouter, route_financial

__all__ = [
    "EodhdAdapter",
    "FinancialFact",
    "FinancialProvider",
    "FinancialProviderResult",
    "FinancialProviderRouter",
    "FinancialRouter",
    "FixtureFinancialAdapter",
    "OfficialFilingAdapter",
    "SECCompanyFactsHttpAdapter",
    "ProviderStatus",
    "TwelveDataAdapter",
    "normalize_financial_result",
    "route_financial_facts",
    "route_financial",
]
