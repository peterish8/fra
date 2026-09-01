"""Replaceable source/snapshot ledger service with a deterministic local adapter."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from threading import RLock
from typing import Protocol
from uuid import UUID

from .families import connected_source_families
from .identity import (
    canonical_document_identity,
    canonical_domain,
    canonicalize_url,
    content_hash,
    metadata_content_hash,
)
from .models import (
    AuthorityTier,
    RetentionMode,
    RunSourceLink,
    SourceOwnership,
    SourceRecord,
    SourceRelationshipRecord,
    SourceRelationshipType,
    SourceSnapshotInput,
    SourceSnapshotRecord,
)


class SourceNotFoundError(LookupError):
    """Requested source/snapshot is absent from the configured ledger."""


class SourceLedgerRepository(Protocol):
    """Persistence protocol implemented by the in-memory adapter below."""

    def save_source(self, source: SourceRecord) -> SourceRecord: ...

    def save_snapshot(self, snapshot: SourceSnapshotRecord) -> SourceSnapshotRecord: ...


class InMemorySourceLedgerRepository:
    """Thread-safe fixture repository; no network or provider calls."""

    def __init__(self) -> None:
        self.sources: dict[UUID, SourceRecord] = {}
        self.snapshots: dict[UUID, SourceSnapshotRecord] = {}
        self.relationships: dict[tuple[UUID, UUID, str], SourceRelationshipRecord] = {}
        self.run_sources: dict[tuple[UUID, UUID], RunSourceLink] = {}
        self._lock = RLock()

    def save_source(self, source: SourceRecord) -> SourceRecord:
        with self._lock:
            self.sources[source.source_id] = source
        return source

    def save_snapshot(self, snapshot: SourceSnapshotRecord) -> SourceSnapshotRecord:
        with self._lock:
            self.snapshots[snapshot.snapshot_id] = snapshot
        return snapshot


class SourceLedgerService:
    """Application-facing source lineage operations.

    A PostgreSQL adapter can implement the same repository behavior while
    preserving these identity, retention, and append-only invariants.
    """

    def __init__(self, repository: InMemorySourceLedgerRepository | None = None) -> None:
        self.repository = repository or InMemorySourceLedgerRepository()

    def create_source(
        self,
        *,
        publisher: str,
        source_type: str,
        authority_tier: AuthorityTier | str,
        canonical_url: str | None = None,
        external_document_id: str | None = None,
        ownership_relation: SourceOwnership = SourceOwnership.UNKNOWN,
        is_primary_source: bool = False,
        language: str | None = None,
    ) -> SourceRecord:
        """Create or return a source by canonical URL/document identity."""

        if canonical_url is not None:
            canonical_url = canonicalize_url(canonical_url)
            domain = canonical_domain(canonical_url)
        else:
            domain = None
        identity = canonical_document_identity(
            canonical_url=canonical_url, external_document_id=external_document_id
        )
        for source in self.repository.sources.values():
            if source.identity_key == identity:
                return source
        return self.repository.save_source(
            SourceRecord(
                publisher=publisher.strip(),
                source_type=source_type.strip(),
                authority_tier=authority_tier,
                canonical_url=canonical_url,
                external_document_id=external_document_id,
                identity_key=identity,
                domain=domain,
                ownership_relation=ownership_relation,
                is_primary_source=is_primary_source,
                language=language,
            )
        )

    upsert_source = create_source

    def record_snapshot(self, snapshot: SourceSnapshotInput) -> SourceSnapshotRecord:
        """Persist an immutable snapshot, deduplicating repeated content hashes."""

        self.get_source(snapshot.source_id)
        digest = snapshot.content_hash
        if digest is None:
            if snapshot.content is not None:
                digest = content_hash(snapshot.content)
            else:
                digest = metadata_content_hash(
                    {
                        "source_id": str(snapshot.source_id),
                        "title": snapshot.title,
                        "published_at": snapshot.published_at,
                        "metadata": snapshot.metadata,
                    }
                )
        elif snapshot.content is not None and digest != content_hash(snapshot.content):
            raise ValueError("content_hash does not match supplied content")
        retained_text = snapshot.permitted_excerpt or snapshot.extracted_text
        if snapshot.retention_mode is RetentionMode.METADATA_ONLY:
            retained_text = None
        elif snapshot.retention_mode is RetentionMode.EXCERPT_ONLY:
            retained_text = snapshot.permitted_excerpt or snapshot.extracted_text
        elif snapshot.retention_mode is RetentionMode.FULL_TEXT:
            if retained_text is None and snapshot.content is not None:
                retained_text = (
                    snapshot.content.decode("utf-8", errors="replace")
                    if isinstance(snapshot.content, bytes)
                    else snapshot.content
                )
        elif snapshot.retention_mode is RetentionMode.STORAGE_REFERENCE:
            retained_text = None
        for existing in self.repository.snapshots.values():
            if existing.source_id == snapshot.source_id and existing.content_hash == digest:
                return existing
        metadata = dict(snapshot.metadata)
        metadata.setdefault("retention_mode", snapshot.retention_mode.value)
        if snapshot.content is not None and snapshot.retention_mode is RetentionMode.METADATA_ONLY:
            metadata.setdefault("content_supplied_but_not_retained", True)
        return self.repository.save_snapshot(
            SourceSnapshotRecord(
                source_id=snapshot.source_id,
                title=snapshot.title,
                published_at=snapshot.published_at,
                retrieved_at=snapshot.retrieved_at or datetime.now(UTC),
                content_hash=digest,
                extracted_text=retained_text,
                storage_ref=snapshot.storage_ref,
                retention_mode=snapshot.retention_mode,
                redirect_chain=tuple(snapshot.redirect_chain),
                metadata=metadata,
            )
        )

    create_snapshot = record_snapshot
    save_snapshot = record_snapshot

    def get_source(self, source_id: UUID) -> SourceRecord:
        try:
            return self.repository.sources[source_id]
        except KeyError as error:
            raise SourceNotFoundError(f"source {source_id} was not found") from error

    def get_snapshot(self, snapshot_id: UUID) -> SourceSnapshotRecord:
        try:
            return self.repository.snapshots[snapshot_id]
        except KeyError as error:
            raise SourceNotFoundError(f"snapshot {snapshot_id} was not found") from error

    def snapshots_for_source(self, source_id: UUID) -> list[SourceSnapshotRecord]:
        self.get_source(source_id)
        return sorted(
            (item for item in self.repository.snapshots.values() if item.source_id == source_id),
            key=lambda item: (item.retrieved_at, str(item.snapshot_id)),
            reverse=True,
        )

    def link_snapshot_to_run(
        self,
        *,
        research_run_id: UUID,
        snapshot_id: UUID,
        discovered_by_provider_request_id: UUID | None = None,
        purpose: str | None = None,
    ) -> RunSourceLink:
        self.get_snapshot(snapshot_id)
        link = RunSourceLink(
            research_run_id=research_run_id,
            snapshot_id=snapshot_id,
            discovered_by_provider_request_id=discovered_by_provider_request_id,
            purpose=purpose,
        )
        self.repository.run_sources[(research_run_id, snapshot_id)] = link
        return link

    def relate_sources(
        self,
        *,
        from_source_id: UUID,
        to_source_id: UUID,
        relationship_type: SourceRelationshipType | str,
        confidence: float,
        explanation: str,
    ) -> SourceRelationshipRecord:
        if from_source_id == to_source_id:
            raise ValueError("source relationships cannot point to the same source")
        self.get_source(from_source_id)
        self.get_source(to_source_id)
        relationship = SourceRelationshipRecord(
            from_source_id=from_source_id,
            to_source_id=to_source_id,
            relationship_type=relationship_type,
            confidence=confidence,
            explanation=explanation,
        )
        key = (from_source_id, to_source_id, str(relationship_type))
        prior = self.repository.relationships.get(key)
        if prior is not None:
            return prior
        self.repository.relationships[key] = relationship
        return relationship

    def relationships_for(self, source_id: UUID) -> list[SourceRelationshipRecord]:
        self.get_source(source_id)
        return [
            relationship
            for relationship in self.repository.relationships.values()
            if relationship.from_source_id == source_id or relationship.to_source_id == source_id
        ]

    def source_families(self, source_ids: Sequence[UUID]) -> list[frozenset[UUID]]:
        relationships = self.repository.relationships.values()
        return connected_source_families(source_ids, relationships)

    get_source_families = source_families

    def independent_source_family_count(self, source_ids: Iterable[UUID]) -> int:
        ids = list(source_ids)
        return len(self.source_families(ids))


__all__ = [
    "InMemorySourceLedgerRepository",
    "SourceLedgerRepository",
    "SourceLedgerService",
    "SourceNotFoundError",
]
