"""Verified-report publication gates and synthesis claim-ID validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PublicationStatus(StrEnum):
    READY = "READY"
    VERIFIED = "VERIFIED"


class PublicationGateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_version_ids: list[UUID] = Field(default_factory=list)
    citation_verified_ids: list[UUID] = Field(default_factory=list)
    blocking_claim_ids: list[UUID] = Field(default_factory=list)
    critical_conflicts: int = Field(default=0, ge=0)
    identity_passed: bool = True
    numeric_passed: bool = True
    temporal_passed: bool = True
    # Percent form (the report API uses 0..100).  The compatibility adapter
    # below also accepts the earlier 0..1 fixture vocabulary.
    citation_coverage: float | None = Field(default=None, ge=0, le=100)
    score_version: str | None = None
    prompt_version: str | None = None
    config_version: str | None = None
    synthesis: Mapping[str, Any] | None = None


class PublicationGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    report_status: PublicationStatus = PublicationStatus.READY
    citation_coverage: float = Field(ge=0, le=100)
    blocking_claims: int = Field(ge=0)
    critical_conflicts: int = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)
    unmapped_claim_sentences: list[str] = Field(default_factory=list)
    # Stable aliases retained for API drafts and older workers.
    allowed: bool
    quality_state: str
    blockers: list[str] = Field(default_factory=list)
    blocking_claim_count: int = Field(ge=0)


def validate_synthesis_claim_mapping(
    synthesis: Mapping[str, Any] | None,
    allowed_claim_version_ids: Iterable[UUID],
) -> list[str]:
    """Reject factual paragraphs that do not map to approved claim versions."""

    if synthesis is None:
        return ["Synthesis output is missing."]
    allowed = {str(value) for value in allowed_claim_version_ids}
    unmapped: list[str] = []
    sections = synthesis.get("sections", [])
    if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes)):
        return ["Synthesis sections are malformed."]
    for section in sections:
        if not isinstance(section, Mapping):
            unmapped.append("<malformed section>")
            continue
        paragraphs = section.get("paragraphs", [])
        if not isinstance(paragraphs, Sequence) or isinstance(paragraphs, (str, bytes)):
            unmapped.append("<malformed paragraphs>")
            continue
        for paragraph in paragraphs:
            if not isinstance(paragraph, Mapping):
                unmapped.append("<malformed paragraph>")
                continue
            text = str(paragraph.get("text", "")).strip()
            mapped = paragraph.get("claim_version_ids", [])
            mapped_ids = (
                {str(value) for value in mapped}
                if isinstance(mapped, Sequence) and not isinstance(mapped, (str, bytes))
                else set()
            )
            if text and not mapped_ids:
                unmapped.append(text)
            elif not mapped_ids.issubset(allowed):
                unmapped.append(text or "<unmapped paragraph>")
    return unmapped


def evaluate_publication_gate(
    value: PublicationGateInput | None = None, **legacy: Any
) -> PublicationGateResult:
    """Return VERIFIED only when all required publication conditions pass."""

    if value is None:
        value = _legacy_publication_input(legacy)

    reasons: list[str] = []
    unmapped = validate_synthesis_claim_mapping(value.synthesis, value.claim_version_ids)
    if value.citation_coverage is not None:
        coverage = value.citation_coverage
    elif value.claim_version_ids:
        coverage = len(set(value.citation_verified_ids) & set(value.claim_version_ids)) / len(
            set(value.claim_version_ids)
        ) * 100
    else:
        coverage = 100.0
    blockers: list[str] = []
    if coverage < 100:
        blockers.append("CITATION_COVERAGE")
        reasons.append("Citation verification coverage is below 100%.")
    if value.blocking_claim_ids:
        blockers.append("CLAIM_VERIFICATION")
        reasons.append("One or more claim-level verification blockers remain.")
    if value.critical_conflicts:
        blockers.append("CRITICAL_CONFLICT")
        reasons.append("Critical conflicts remain unresolved or would be hidden.")
    if not value.identity_passed:
        blockers.append("IDENTITY")
        reasons.append("Required identity verification did not pass.")
    if not value.numeric_passed:
        blockers.append("NUMERIC")
        reasons.append("Required numeric verification did not pass.")
    if not value.temporal_passed:
        blockers.append("TEMPORAL")
        reasons.append("Required temporal verification did not pass.")
    if not value.score_version or not value.prompt_version or not value.config_version:
        blockers.append("VERSION")
        reasons.append("Score, prompt, and config versions are required.")
    if unmapped:
        blockers.append("UNMAPPED_FACT")
        reasons.append("Synthesis contains factual text not mapped to approved claim versions.")
    passed = not reasons
    blocking_count = len(value.blocking_claim_ids) or (0 if passed else 1)
    return PublicationGateResult(
        passed=passed,
        report_status=PublicationStatus.VERIFIED if passed else PublicationStatus.READY,
        citation_coverage=round(coverage, 4),
        blocking_claims=len(value.blocking_claim_ids),
        critical_conflicts=value.critical_conflicts,
        reasons=reasons,
        unmapped_claim_sentences=unmapped,
        allowed=passed,
        quality_state=PublicationStatus.VERIFIED.value if passed else PublicationStatus.READY.value,
        blockers=blockers,
        blocking_claim_count=blocking_count,
    )


check_publication_gate = evaluate_publication_gate
PublicationGate = PublicationGateInput


def validate_synthesis_mapping(
    synthesis: Mapping[str, Any], allowed_claim_version_ids: Iterable[UUID]
) -> None:
    """Raise before publication when any factual paragraph lacks a claim ID."""

    unmapped = validate_synthesis_claim_mapping(synthesis, allowed_claim_version_ids)
    if unmapped:
        raise ValueError("unmapped synthesis facts: " + "; ".join(unmapped))


check_synthesis_mapping = validate_synthesis_mapping


def _legacy_publication_input(values: dict[str, Any]) -> PublicationGateInput:
    raw_coverage = float(values.get("citation_coverage", 0))
    coverage = raw_coverage * 100 if 0 <= raw_coverage <= 1 else raw_coverage
    unmapped = values.get("unmapped_facts", [])
    if not isinstance(unmapped, list):
        unmapped = list(unmapped) if isinstance(unmapped, Sequence) else [str(unmapped)]
    synthesis = {
        "sections": [
            {"paragraphs": [{"text": str(fact), "claim_version_ids": []} for fact in unmapped]}
        ]
    }
    return PublicationGateInput(
        citation_coverage=coverage,
        identity_passed=bool(values.get("identity_complete", True)),
        numeric_passed=str(values.get("numeric_check", "PASS")).upper() == "PASS",
        temporal_passed=str(values.get("temporal_check", "PASS")).upper() == "PASS",
        critical_conflicts=1 if values.get("critical_conflict", False) else 0,
        score_version=values.get("score_version"),
        prompt_version=values.get("prompt_version"),
        config_version=values.get("config_version"),
        synthesis=synthesis if unmapped else {"sections": []},
    )


__all__ = [
    "PublicationGate",
    "PublicationGateInput",
    "PublicationGateResult",
    "PublicationStatus",
    "check_publication_gate",
    "check_synthesis_mapping",
    "evaluate_publication_gate",
    "validate_synthesis_mapping",
    "validate_synthesis_claim_mapping",
]
