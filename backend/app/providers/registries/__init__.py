"""Official-first registry adapter contracts."""

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
    "normalize_registry_result",
]
