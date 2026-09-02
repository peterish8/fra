"""Source-family and fake-consensus classification."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import SourceRecord, SourceRelationshipRecord, SourceRelationshipType

_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)

_FAMILY_RELATIONSHIPS = frozenset(
    {
        SourceRelationshipType.DUPLICATE_OF,
        SourceRelationshipType.SYNDICATED_FROM,
        SourceRelationshipType.DERIVED_FROM,
        SourceRelationshipType.DERIVED_FROM_COMPANY_RELEASE,
        SourceRelationshipType.QUOTES,
        SourceRelationshipType.SHARED_ROOT,
    }
)


class SourceFamilyMember(BaseModel):
    """Typed observation used to build source-family evidence summaries.

    A source may appear once per provider observation.  ``source_id`` remains
    the stable document identity, while provider and URL values are metadata
    used only to explain multiplicity.  They never create independent support
    on their own.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: UUID
    root_source_id: UUID | None = None
    canonical_url: str | None = None
    provider_id: str | None = None
    independent_eligible: bool = True

    @field_validator("canonical_url", "provider_id")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SourceFamilySummary(BaseModel):
    """Deterministic family-level support data for reconciliation.

    ``source_count``, ``url_count`` and ``provider_count`` are diagnostic
    multiplicity only.  Reconciliation should use ``independent`` and count
    summaries, never any of those raw counts.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    root_source_id: UUID
    source_ids: tuple[UUID, ...]
    canonical_urls: tuple[str, ...] = ()
    provider_ids: tuple[str, ...] = ()
    independent: bool
    source_count: int = Field(ge=0)
    url_count: int = Field(ge=0)
    provider_count: int = Field(ge=0)


def _family_components(
    source_ids: Iterable[UUID],
    relationships: Iterable[SourceRelationshipRecord],
    *,
    members: Sequence[SourceFamilyMember] = (),
) -> list[frozenset[UUID]]:
    """Return stable connected components for accepted common-root edges."""

    # ``source_ids`` is the set of observations selected for this operation.
    # A member's canonical root is allowed to be outside that set (for
    # example, a provider observation can point at a persisted Reuters source
    # that was not itself returned by the provider).  Keep those root IDs in
    # the union-find universe, but never expose them as extra observations.
    selected_ids = set(source_ids)
    member_list = tuple(members)
    if not selected_ids and member_list:
        selected_ids = {member.source_id for member in member_list}

    ids = set(selected_ids)
    ids.update(member.source_id for member in member_list)
    ids.update(
        member.root_source_id
        for member in member_list
        if member.root_source_id is not None
    )
    accepted_relationships = tuple(
        relationship
        for relationship in relationships
        if relationship.relationship_type in _FAMILY_RELATIONSHIPS
    )
    ids.update(
        endpoint
        for relationship in accepted_relationships
        for endpoint in (relationship.from_source_id, relationship.to_source_id)
    )
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

    # A persisted canonical root is stronger than provider/URL multiplicity.
    for member in members:
        if member.root_source_id is not None:
            union(member.source_id, member.root_source_id)

    # Exact canonical URLs represent the same logical source even if separate
    # provider observations produced separate source IDs.
    first_by_url: dict[str, UUID] = {}
    for member in members:
        if member.canonical_url is None:
            continue
        prior = first_by_url.setdefault(member.canonical_url, member.source_id)
        union(prior, member.source_id)

    for relationship in accepted_relationships:
        union(relationship.from_source_id, relationship.to_source_id)

    groups: dict[UUID, set[UUID]] = {}
    for source_id in selected_ids:
        groups.setdefault(find(source_id), set()).add(source_id)
    return sorted(
        (frozenset(group) for group in groups.values()),
        key=lambda group: min(str(source_id) for source_id in group),
    )


def source_family_summaries(
    source_ids: Iterable[UUID],
    relationships: Iterable[SourceRelationshipRecord],
    *,
    members: Sequence[SourceFamilyMember] = (),
) -> list[SourceFamilySummary]:
    """Build family summaries whose independence is root-based.

    URL and provider multiplicity is retained as diagnostic metadata, but a
    family contributes at most one independent unit.  If a family contains a
    known ineligible root (such as a company-owned press release), it is not
    counted as independent even when copies are hosted elsewhere.
    """

    member_list = tuple(members)
    components = _family_components(source_ids, relationships, members=member_list)
    if not components:
        return []

    summaries: list[SourceFamilySummary] = []
    for component in components:
        component_root_ids = {
            member.root_source_id or member.source_id
            for member in member_list
            if member.source_id in component
            or (member.root_source_id is not None and member.root_source_id in component)
        }
        component_members = [
            member
            for member in member_list
            if member.source_id in component
            or (member.root_source_id is not None and member.root_source_id in component)
            or member.source_id in component_root_ids
        ]
        root_ids = {
            member.root_source_id or member.source_id for member in component_members
        }
        root_source_id = min(root_ids or component, key=str)
        canonical_urls = tuple(
            sorted(
                {
                    member.canonical_url
                    for member in component_members
                    if member.canonical_url is not None
                }
            )
        )
        provider_ids = tuple(
            sorted(
                {
                    member.provider_id
                    for member in component_members
                    if member.provider_id is not None
                }
            )
        )
        # Missing metadata is conservatively treated as eligible for
        # backwards compatibility; an explicitly ineligible root makes the
        # whole common-origin family non-independent.
        independent = all(member.independent_eligible for member in component_members)
        summaries.append(
            SourceFamilySummary(
                root_source_id=root_source_id,
                source_ids=tuple(sorted(component, key=str)),
                canonical_urls=canonical_urls,
                provider_ids=provider_ids,
                independent=independent,
                source_count=len(component),
                url_count=len(canonical_urls),
                provider_count=len(provider_ids),
            )
        )
    return summaries


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
    *,
    members: Sequence[SourceFamilyMember] = (),
) -> list[frozenset[UUID]]:
    """Return connected components representing independent source families.

    ``members`` is optional for compatibility with the original source-ID API.
    When provided, persisted roots and canonical URLs collapse provider
    observations before family membership is returned.
    """

    return _family_components(source_ids, relationships, members=members)


def independent_family_count(
    source_ids: Iterable[UUID],
    relationships: Iterable[SourceRelationshipRecord],
    *,
    members: Sequence[SourceFamilyMember] = (),
) -> int:
    """Count independent root families, never provider or URL multiplicity."""

    summaries = source_family_summaries(source_ids, relationships, members=members)
    return sum(summary.independent for summary in summaries)


__all__ = [
    "SourceFamilyClassifier",
    "SourceFamilyMember",
    "SourceFamilySummary",
    "classify_source_relationship",
    "connected_source_families",
    "independent_family_count",
    "source_family_summaries",
]
