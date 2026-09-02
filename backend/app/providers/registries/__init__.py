"""Official-first registry adapter contracts."""

from .companies_house import CompaniesHouseHttpAdapter
from .contracts import (
    LegalEntityRecord,
    NormalizedRegistryResult,
    ProviderStatus,
    RegistryAdapter,
    normalize_registry_result,
)
from .gleif import GLEIFHttpAdapter

__all__ = [
    "LegalEntityRecord",
    "NormalizedRegistryResult",
    "ProviderStatus",
    "RegistryAdapter",
    "GLEIFHttpAdapter",
    "CompaniesHouseHttpAdapter",
    "normalize_registry_result",
]
