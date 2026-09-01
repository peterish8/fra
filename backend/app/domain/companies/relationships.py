"""Version-preserving company relationship normalization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RelationshipRecord(BaseModel):
    """Relationship lineage with dates and evidence kept as supplied."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    relationship_id: str | None = None
    from_company_id: str = Field(min_length=1)
    to_company_id: str = Field(min_length=1)
    relationship_type: str = Field(min_length=1)
    entity_scope: str = Field(min_length=1)
    effective_from: str | None = None
    effective_to: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


def normalize_relationship_history(
    relationships: Sequence[Mapping[str, Any] | RelationshipRecord],
) -> list[dict[str, Any]]:
    """Validate and normalize relationship history without collapsing records."""

    normalized: list[dict[str, Any]] = []
    for relationship in relationships:
        record = (
            relationship
            if isinstance(relationship, RelationshipRecord)
            else RelationshipRecord.model_validate(relationship)
        )
        normalized.append(record.model_dump(exclude_none=False))
    return normalized


__all__ = ["RelationshipRecord", "normalize_relationship_history"]
