"""Claim-domain boundaries."""

from .ownership import (
    OwnershipClassification,
    OwnershipDecision,
    classify_ownership,
    classify_source_ownership,
    exclude_company_owned_domains,
    is_company_owned,
)

__all__ = [
    "OwnershipClassification",
    "OwnershipDecision",
    "classify_ownership",
    "classify_source_ownership",
    "exclude_company_owned_domains",
    "is_company_owned",
]
