"""Official-first registry adapter contracts."""

from .contracts import (
    LegalEntityRecord,
    NormalizedRegistryResult,
    ProviderStatus,
    RegistryAdapter,
    normalize_registry_result,
)

__all__ = [
    "LegalEntityRecord",
    "NormalizedRegistryResult",
    "ProviderStatus",
    "RegistryAdapter",
    "normalize_registry_result",
]
