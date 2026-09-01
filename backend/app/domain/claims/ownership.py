"""Company-owned versus independent source classification."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.domain.sources.identity import canonical_domain
from app.domain.sources.models import SourceOwnership


class OwnershipDecision(StrEnum):
    """Decision state for domain ownership evidence."""

    CONFIRMED = "CONFIRMED"
    UNCONFIRMED = "UNCONFIRMED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OwnershipClassification(BaseModel):
    """Explainable ownership result consumed by claim planning/verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relation: SourceOwnership
    decision: OwnershipDecision
    confidence: float = Field(ge=0, le=1)
    independent_eligible: bool
    normalized_domain: str | None = None
    matched_company_domain: str | None = None
    explanation: str = Field(min_length=1)


_COMPANY_SOURCE_TYPES = frozenset(
    {"COMPANY_WEBSITE", "COMPANY_PRESS_RELEASE", "COMPANY_BLOG", "INVESTOR_RELATIONS", "PR"}
)
_GOVERNMENT_SOURCE_TYPES = frozenset({"GOVERNMENT", "REGULATOR", "REGISTRY"})
_FILING_SOURCE_TYPES = frozenset({"FILING", "REGULATORY_FILING", "ANNUAL_REPORT"})
_STRUCTURED_SOURCE_TYPES = frozenset({"STRUCTURED_PROVIDER", "FINANCIAL_API", "DATA_PROVIDER"})


def classify_ownership(
    *,
    source_domain: str | None,
    company_domains: Iterable[str] = (),
    source_type: str | None = None,
    publisher: str | None = None,
    confirmed_company_domains: Iterable[str] = (),
    authoritative_domain_confirmation: bool = False,
) -> OwnershipClassification:
    """Classify ownership without treating an unconfirmed domain as official."""

    normalized_source = _safe_domain(source_domain)
    confirmed = {_safe_domain(value) for value in confirmed_company_domains}
    confirmed.discard(None)
    known = {_safe_domain(value) for value in company_domains}
    known.discard(None)
    source_kind = (source_type or "").strip().upper().replace("-", "_")
    matched = normalized_source if normalized_source in confirmed else None
    if matched is None and normalized_source in known and authoritative_domain_confirmation:
        matched = normalized_source
    if source_kind in _GOVERNMENT_SOURCE_TYPES:
        return OwnershipClassification(
            relation=SourceOwnership.GOVERNMENT
            if source_kind == "GOVERNMENT"
            else SourceOwnership.REGULATOR,
            decision=OwnershipDecision.NOT_APPLICABLE,
            confidence=0.95,
            independent_eligible=True,
            normalized_domain=normalized_source,
            explanation="Government/regulator source is not company-owned content.",
        )
    if source_kind in _FILING_SOURCE_TYPES:
        return OwnershipClassification(
            relation=SourceOwnership.FILING,
            decision=OwnershipDecision.NOT_APPLICABLE,
            confidence=0.95,
            independent_eligible=True,
            normalized_domain=normalized_source,
            explanation="A filing is classified by its regulatory source context.",
        )
    if source_kind in _STRUCTURED_SOURCE_TYPES:
        return OwnershipClassification(
            relation=SourceOwnership.STRUCTURED_PROVIDER,
            decision=OwnershipDecision.NOT_APPLICABLE,
            confidence=0.9,
            independent_eligible=True,
            normalized_domain=normalized_source,
            explanation="Structured provider output is an independent provider-origin record.",
        )
    if matched is not None:
        return OwnershipClassification(
            relation=SourceOwnership.SELF_REPORTED,
            decision=OwnershipDecision.CONFIRMED,
            confidence=1.0 if authoritative_domain_confirmation else 0.9,
            independent_eligible=False,
            normalized_domain=normalized_source,
            matched_company_domain=matched,
            explanation=(
                "Authoritatively confirmed company domain; statements remain self-reported."
            ),
        )
    if normalized_source in known or source_kind in _COMPANY_SOURCE_TYPES:
        return OwnershipClassification(
            relation=SourceOwnership.UNCONFIRMED,
            decision=OwnershipDecision.UNCONFIRMED,
            confidence=0.25,
            independent_eligible=False,
            normalized_domain=normalized_source,
            explanation="Candidate company ownership is not authoritatively confirmed.",
        )
    if source_domain is None and publisher is None:
        return OwnershipClassification(
            relation=SourceOwnership.UNKNOWN,
            decision=OwnershipDecision.UNCONFIRMED,
            confidence=0.0,
            independent_eligible=False,
            explanation="No source domain or publisher evidence was supplied.",
        )
    return OwnershipClassification(
        relation=SourceOwnership.INDEPENDENT,
        decision=OwnershipDecision.NOT_APPLICABLE,
        confidence=0.5,
        independent_eligible=True,
        normalized_domain=normalized_source,
        explanation="No company-ownership relationship was established at this boundary.",
    )


classify_source_ownership = classify_ownership


def is_company_owned(
    source_domain: str | None,
    company_domains: Iterable[str],
    *,
    confirmed_company_domains: Iterable[str] = (),
) -> bool:
    """Return true only for confirmed company-owned domains."""

    decision = classify_ownership(
        source_domain=source_domain,
        company_domains=company_domains,
        confirmed_company_domains=confirmed_company_domains,
    )
    return decision.relation is SourceOwnership.SELF_REPORTED


def exclude_company_owned_domains(
    domains_or_urls: Sequence[str],
    company_domains: Iterable[str],
    *,
    confirmed_company_domains: Iterable[str] = (),
) -> list[str]:
    """Exclude confirmed company domains from independent search inputs."""

    known = {_safe_domain(value) for value in company_domains}
    confirmed = {_safe_domain(value) for value in confirmed_company_domains}
    known.discard(None)
    confirmed.discard(None)
    # If explicit confirmation is absent, candidate domains remain visible to
    # callers but are not silently treated as official or excluded.
    excluded = confirmed or set()
    return [value for value in domains_or_urls if _safe_domain(value) not in excluded]


def _safe_domain(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return canonical_domain(value)
    except ValueError:
        return None


__all__ = [
    "OwnershipClassification",
    "OwnershipDecision",
    "classify_ownership",
    "classify_source_ownership",
    "exclude_company_owned_domains",
    "is_company_owned",
]
