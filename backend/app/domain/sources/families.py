"""Source-family and fake-consensus classification."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from .models import SourceRecord, SourceRelationshipRecord, SourceRelationshipType

_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


def _normalized_text(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE.sub(" ", _PUNCTUATION.sub(" ", value.casefold())).strip()


def classify_source_relationship(
    source: SourceRecord,
    other: SourceRecord,
    *,
    source_metadata: dict[str, Any] | None = None,
    other_metadata: dict[str, Any] | None = None,
    source_text: str | None = None,
    other_text: str | None = None,
    near_duplicate_threshold: float = 0.92,
) -> tuple[SourceRelationshipType, float, str] | None:
    """Return a relationship when two sources share a likely root origin."""

    if source.source_id == other.source_id:
        return None
    left = source_metadata or {}
    right = other_metadata or {}
    explicit_pairs = (
        ("syndicated_from", SourceRelationshipType.SYNDICATED_FROM),
        ("original_url", SourceRelationshipType.DERIVED_FROM),
        ("source_url", SourceRelationshipType.QUOTES),
        ("quoted_source", SourceRelationshipType.QUOTES),
        ("shared_root_source_id", SourceRelationshipType.SHARED_ROOT),
    )
    for key, relationship in explicit_pairs:
        value = right.get(key)
        if value and (
            str(value) == str(source.canonical_url) or str(value) == str(source.source_id)
        ):
            if key == "original_url" and _looks_like_company_source(source):
                relationship = SourceRelationshipType.DERIVED_FROM_COMPANY_RELEASE
            return relationship, 0.99, f"Metadata field {key} identifies the source root."
        value = left.get(key)
        if value and (str(value) == str(other.canonical_url) or str(value) == str(other.source_id)):
            if key == "original_url" and _looks_like_company_source(other):
                relationship = SourceRelationshipType.DERIVED_FROM_COMPANY_RELEASE
            return relationship, 0.99, f"Metadata field {key} identifies the source root."

    if source.canonical_url and source.canonical_url == other.canonical_url:
        return SourceRelationshipType.DUPLICATE_OF, 1.0, "Sources have the same canonical URL."
    left_hash = left.get("content_hash")
    right_hash = right.get("content_hash")
    if left_hash and left_hash == right_hash:
        return SourceRelationshipType.DUPLICATE_OF, 1.0, "Sources have the same content hash."
    if source_text and other_text:
        left_text = _normalized_text(source_text)
        right_text = _normalized_text(other_text)
        if left_text and right_text:
            similarity = SequenceMatcher(None, left_text, right_text).ratio()
            if similarity >= near_duplicate_threshold:
                return (
                    SourceRelationshipType.DUPLICATE_OF,
                    round(similarity, 4),
                    "Source text is a near-duplicate after normalization.",
                )
    return None


def _looks_like_company_source(source: SourceRecord) -> bool:
    source_type = source.source_type.casefold().replace("-", "_")
    return source.publisher.casefold() in {"company", "corporate"} or source_type in {
        "company_website",
        "company_press_release",
        "company_blog",
        "investor_relations",
    }


class SourceFamilyClassifier:
    """Group related source IDs while retaining each source URL."""

    def classify(
        self,
        sources: Sequence[SourceRecord],
        *,
        metadata: dict[UUID, dict[str, Any]] | None = None,
        text: dict[UUID, str] | None = None,
    ) -> list[SourceRelationshipRecord]:
        relationships: list[SourceRelationshipRecord] = []
        metadata = metadata or {}
        text = text or {}
        for index, source in enumerate(sources):
            for other in sources[index + 1 :]:
                match = classify_source_relationship(
                    source,
                    other,
                    source_metadata=metadata.get(source.source_id),
                    other_metadata=metadata.get(other.source_id),
                    source_text=text.get(source.source_id),
                    other_text=text.get(other.source_id),
                )
                if match is None:
                    continue
                relationship, confidence, explanation = match
                relationships.append(
                    SourceRelationshipRecord(
                        from_source_id=source.source_id,
                        to_source_id=other.source_id,
                        relationship_type=relationship,
                        confidence=confidence,
                        explanation=explanation,
                    )
                )
        return relationships


def connected_source_families(
    source_ids: Iterable[UUID],
    relationships: Iterable[SourceRelationshipRecord],
) -> list[frozenset[UUID]]:
    """Return connected components representing independent source families."""

    ids = set(source_ids)
    parent = {source_id: source_id for source_id in ids}

    def find(value: UUID) -> UUID:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: UUID, right: UUID) -> None:
        if left not in parent or right not in parent:
            return
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for relationship in relationships:
        if relationship.relationship_type in {
            SourceRelationshipType.DUPLICATE_OF,
            SourceRelationshipType.SYNDICATED_FROM,
            SourceRelationshipType.DERIVED_FROM,
            SourceRelationshipType.DERIVED_FROM_COMPANY_RELEASE,
            SourceRelationshipType.QUOTES,
            SourceRelationshipType.SHARED_ROOT,
        }:
            union(relationship.from_source_id, relationship.to_source_id)
    groups: dict[UUID, set[UUID]] = {}
    for source_id in ids:
        groups.setdefault(find(source_id), set()).add(source_id)
    return [frozenset(group) for group in groups.values()]


def independent_family_count(
    source_ids: Iterable[UUID], relationships: Iterable[SourceRelationshipRecord]
) -> int:
    """Count source families rather than URLs or provider result count."""

    return len(connected_source_families(source_ids, relationships))


__all__ = [
    "SourceFamilyClassifier",
    "classify_source_relationship",
    "connected_source_families",
    "independent_family_count",
]
