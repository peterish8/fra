"""Atomic claim construction and evidence mapping."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.providers.llm.contracts import CompanyClaimExtractionEnvelope, ExtractedClaim

from .models import (
    ClaimInput,
    ClaimOrigin,
    ClaimRecord,
    ClaimVersionRecord,
    EvidenceRelationRecord,
    EvidenceRole,
)
from .repository import ClaimRepository, InMemoryClaimRepository

_SPACE = re.compile(r"\s+")


def canonical_claim_key(
    statement: str,
    *,
    category: str,
    company_id: UUID | None = None,
) -> str:
    """Create a stable key for one proposition across research refreshes."""

    normalized = _SPACE.sub(" ", statement.strip().casefold())
    period = re.search(r"\b(FY\d{4}|CY\d{4}|Q[1-4]\s*FY?\d{4})\b", statement, re.IGNORECASE)
    if "revenue" in normalized and any(
        word in normalized for word in ("grew", "increased", "growth")
    ):
        # A caller may later replace CURRENT/FY labels with a period extracted
        # from a typed fact; the fallback preserves a stable claim key without
        # changing the wording or asserting a historical period.
        return f"revenue-growth:{period.group(1).upper() if period else 'UNKNOWN_PERIOD'}"
    if "customer" in normalized and any(
        word in normalized for word in ("serve", "served", "customer count")
    ):
        return "customer-count:CURRENT"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    company = str(company_id) if company_id is not None else "global"
    return f"{company}:{category.strip().casefold()}:{digest}"


def split_compound_claim(statement: str) -> list[str]:
    """Split common compound propositions without inventing new wording."""

    normalized = statement.strip()
    if not normalized:
        return []
    pieces = re.split(r"\s*;\s*|\s+(?:and|but)\s+", normalized, flags=re.IGNORECASE)
    result = [piece.strip(" ,") for piece in pieces if piece.strip(" ,")]
    return result or [normalized]


class ClaimService:
    """Build append-only claims and evidence without provider dependencies."""

    def __init__(
        self,
        repository: ClaimRepository | None = None,
        *,
        snapshot_exists: Callable[[UUID], bool] | None = None,
    ) -> None:
        self.repository = repository or InMemoryClaimRepository()
        self.snapshot_exists = snapshot_exists

    def create(self, request: ClaimInput) -> tuple[ClaimRecord, ClaimVersionRecord]:
        key = request.canonical_key or canonical_claim_key(
            request.statement, category=request.category, company_id=request.company_id
        )
        claim = self._find_claim(request.company_id, key)
        if claim is None:
            claim = self.repository.save_claim(
                ClaimRecord(
                    company_id=request.company_id,
                    canonical_key=key,
                    category=request.category,
                    origin=request.origin,
                    materiality=request.materiality,
                )
            )
        version = self.repository.save_version(
            ClaimVersionRecord(
                claim_id=claim.claim_id,
                research_run_id=request.research_run_id,
                statement=request.statement,
                structured_value=request.structured_value,
                supersedes_claim_version_id=self._latest_version_id(claim.claim_id),
            )
        )
        return claim, version

    def from_extracted(
        self,
        claim: ExtractedClaim,
        *,
        origin: ClaimOrigin,
        source_snapshot_id: UUID | None = None,
        company_id: UUID | None = None,
        research_run_id: UUID | None = None,
    ) -> tuple[ClaimRecord, ClaimVersionRecord, EvidenceRelationRecord]:
        snapshot_id = claim.source_snapshot_id or source_snapshot_id
        if snapshot_id is None:
            raise ValueError("claim extraction must identify a source snapshot")
        claim_record, version = self.create(
            ClaimInput(
                statement=claim.statement,
                category=claim.category,
                origin=origin,
                materiality=claim.materiality.value,
                company_id=company_id,
                research_run_id=research_run_id,
                structured_value=claim.structured_value,
            )
        )
        evidence = self.add_evidence(
            claim_version_id=version.claim_version_id,
            source_snapshot_id=snapshot_id,
            evidence_role=EvidenceRole.ORIGIN
            if origin is ClaimOrigin.SELF_REPORTED
            else EvidenceRole.SUPPORTS,
            excerpt=claim.evidence_excerpt,
            locator=claim.evidence_locator,
            is_independent=origin is not ClaimOrigin.SELF_REPORTED,
            directness=1.0,
        )
        return claim_record, version, evidence

    def from_envelope(
        self,
        envelope: CompanyClaimExtractionEnvelope,
        *,
        origin: ClaimOrigin,
        source_snapshot_id: UUID | None = None,
        company_id: UUID | None = None,
        research_run_id: UUID | None = None,
    ) -> list[tuple[ClaimRecord, ClaimVersionRecord, EvidenceRelationRecord]]:
        results: list[tuple[ClaimRecord, ClaimVersionRecord, EvidenceRelationRecord]] = []
        for item in envelope.claims:
            atomic_items = [
                item.model_copy(update={"statement": statement})
                for statement in split_compound_claim(item.statement)
            ]
            for atomic_item in atomic_items:
                results.append(
                    self.from_extracted(
                        atomic_item,
                        origin=origin,
                        source_snapshot_id=envelope.source_snapshot_id or source_snapshot_id,
                        company_id=company_id,
                        research_run_id=research_run_id,
                    )
                )
        return results

    def from_statement(
        self,
        statement: str,
        *,
        category: str,
        origin: ClaimOrigin,
        company_id: UUID | None = None,
        research_run_id: UUID | None = None,
    ) -> list[tuple[ClaimRecord, ClaimVersionRecord]]:
        """Construct independently verifiable claim versions from a compound statement."""

        return [
            self.create(
                ClaimInput(
                    statement=piece,
                    category=category,
                    origin=origin,
                    company_id=company_id,
                    research_run_id=research_run_id,
                )
            )
            for piece in split_compound_claim(statement)
        ]

    build_atomic_claims = from_statement
    create_from_statement = from_statement

    def add_evidence(
        self,
        *,
        claim_version_id: UUID,
        source_snapshot_id: UUID,
        evidence_role: EvidenceRole,
        excerpt: str | None,
        locator: dict[str, Any] | None = None,
        is_independent: bool,
        directness: float | None,
    ) -> EvidenceRelationRecord:
        if not self.repository.has_version(claim_version_id):
            raise ValueError("claim version does not exist")
        if self.snapshot_exists is not None and not self.snapshot_exists(source_snapshot_id):
            raise ValueError("evidence source snapshot does not exist")
        return self.repository.save_evidence(
            EvidenceRelationRecord(
                claim_version_id=claim_version_id,
                source_snapshot_id=source_snapshot_id,
                evidence_role=evidence_role,
                excerpt=excerpt,
                locator=locator or {},
                is_independent=is_independent,
                directness=directness,
            )
        )

    def _find_claim(self, company_id: UUID | None, canonical_key: str) -> ClaimRecord | None:
        return self.repository.find_claim(company_id, canonical_key)

    def _latest_version_id(self, claim_id: UUID) -> UUID | None:
        latest = self.repository.latest_version(claim_id)
        return latest.claim_version_id if latest is not None else None


__all__ = ["ClaimService", "canonical_claim_key", "split_compound_claim"]
