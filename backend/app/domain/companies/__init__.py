"""Canonical company identity and relationship domain contracts."""

from .models import (
    CompanyCandidate,
    EntityQuery,
    EntityResolution,
    MatchReason,
    ResolutionStatus,
)
from .resolver import resolve_entity

__all__ = [
    "CompanyCandidate",
    "EntityQuery",
    "EntityResolution",
    "MatchReason",
    "ResolutionStatus",
    "resolve_entity",
]
