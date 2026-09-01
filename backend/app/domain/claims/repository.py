"""Replaceable persistence boundary for claim lineage."""

from __future__ import annotations

from collections.abc import Sequence
from threading import RLock
from typing import Protocol
from uuid import UUID

from .models import ClaimRecord, ClaimVersionRecord, EvidenceRelationRecord


class ClaimRepository(Protocol):
    def save_claim(self, claim: ClaimRecord) -> ClaimRecord: ...

    def save_version(self, version: ClaimVersionRecord) -> ClaimVersionRecord: ...

    def save_evidence(self, evidence: EvidenceRelationRecord) -> EvidenceRelationRecord: ...

    def find_claim(self, company_id: UUID | None, canonical_key: str) -> ClaimRecord | None: ...

    def has_version(self, claim_version_id: UUID) -> bool: ...

    def latest_version(self, claim_id: UUID) -> ClaimVersionRecord | None: ...


class InMemoryClaimRepository:
    """Deterministic append-oriented repository for local development."""

    def __init__(self) -> None:
        self.claims: dict[UUID, ClaimRecord] = {}
        self.versions: dict[UUID, ClaimVersionRecord] = {}
        self.evidence: dict[UUID, EvidenceRelationRecord] = {}
        self._lock = RLock()

    def save_claim(self, claim: ClaimRecord) -> ClaimRecord:
        with self._lock:
            self.claims[claim.claim_id] = claim
        return claim

    def save_version(self, version: ClaimVersionRecord) -> ClaimVersionRecord:
        with self._lock:
            self.versions[version.claim_version_id] = version
        return version

    def save_evidence(self, evidence: EvidenceRelationRecord) -> EvidenceRelationRecord:
        with self._lock:
            self.evidence[evidence.evidence_id] = evidence
        return evidence

    def versions_for_claim(self, claim_id: UUID) -> Sequence[ClaimVersionRecord]:
        return [version for version in self.versions.values() if version.claim_id == claim_id]

    def evidence_for_version(self, claim_version_id: UUID) -> Sequence[EvidenceRelationRecord]:
        return [
            item for item in self.evidence.values() if item.claim_version_id == claim_version_id
        ]

    def find_claim(self, company_id: UUID | None, canonical_key: str) -> ClaimRecord | None:
        return next(
            (
                claim
                for claim in self.claims.values()
                if claim.company_id == company_id and claim.canonical_key == canonical_key
            ),
            None,
        )

    def has_version(self, claim_version_id: UUID) -> bool:
        return claim_version_id in self.versions

    def latest_version(self, claim_id: UUID) -> ClaimVersionRecord | None:
        versions = [version for version in self.versions.values() if version.claim_id == claim_id]
        return max(versions, key=lambda item: item.created_at) if versions else None


__all__ = ["ClaimRepository", "InMemoryClaimRepository"]
