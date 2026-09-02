"""Bounded adversarial verification contracts.

Adversarial research searches for evidence that could weaken or qualify a
claim. Its output is evidence for deterministic verification, never a verdict
or an authoritative replacement for a stored claim version.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROMPT_VERSION = "adversarial-v1"
SCHEMA_VERSION = "adversarial-v1"


class AdversarialFocus(StrEnum):
    CONTRADICTION = "CONTRADICTION"
    NEWER_EVIDENCE = "NEWER_EVIDENCE"
    DEFINITION_CHANGE = "DEFINITION_CHANGE"
    MARKET_EXIT = "MARKET_EXIT"
    REGULATORY_ACTION = "REGULATORY_ACTION"
    RESTATEMENT = "RESTATEMENT"
    ALTERNATIVE_ESTIMATE = "ALTERNATIVE_ESTIMATE"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"


class AdversarialOutcome(StrEnum):
    NO_NEW_EVIDENCE = "NO_NEW_EVIDENCE"
    COUNTEREVIDENCE = "COUNTEREVIDENCE"
    MIXED = "MIXED"
    SUPPORTIVE_CONTEXT = "SUPPORTIVE_CONTEXT"


class AdversarialQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    focus: AdversarialFocus
    intent: str = Field(min_length=1, max_length=500)
    query: str = Field(min_length=1, max_length=8_000)
    preferred_source_types: list[str] = Field(default_factory=list, max_length=8)


class AdversarialPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SCHEMA_VERSION
    prompt_version: str = PROMPT_VERSION
    claim_id: str | None = None
    claim: str = Field(min_length=1, max_length=4_000)
    materiality: str = Field(min_length=1, max_length=20)
    queries: list[AdversarialQuery] = Field(default_factory=list, max_length=8)
    max_queries: int = Field(default=4, ge=1, le=8)
    eligible: bool = True
    eligibility_reason: str = Field(min_length=1)


class AdversarialEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str | None = None
    source_url: str | None = None
    excerpt: str = Field(min_length=1, max_length=20_000)
    published_at: str | None = None
    source_type: str | None = None
    source_family_id: str | None = None
    supports_claim: bool | None = None

    @field_validator("excerpt")
    @classmethod
    def trim_excerpt(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("adversarial evidence excerpt must not be blank")
        return normalized


class AdversarialResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SCHEMA_VERSION
    prompt_version: str = PROMPT_VERSION
    claim_id: str | None = None
    focus: AdversarialFocus
    query: str = Field(min_length=1, max_length=8_000)
    outcome: AdversarialOutcome = AdversarialOutcome.NO_NEW_EVIDENCE
    evidence: list[AdversarialEvidence] = Field(default_factory=list, max_length=100)
    explanation: str = Field(min_length=1, max_length=4_000)
    model_version: str = Field(default="fixture-adversarial-v1", min_length=1, max_length=200)
    needs_follow_up: bool = False
    authoritative: bool = False
    verdict: None = None


def is_adversarial_eligible(
    claim: Mapping[str, Any] | str,
    *,
    unresolved: bool = False,
    key_conclusion: bool = False,
    one_sided_support: bool = False,
) -> bool:
    materiality = _claim_materiality(claim)
    return (
        materiality in {"HIGH", "CRITICAL"}
        or key_conclusion
        or one_sided_support
        or unresolved and materiality in {"MEDIUM", "HIGH", "CRITICAL"}
    )


def build_adversarial_plan(
    claim: Mapping[str, Any] | str,
    evidence_gaps: Iterable[str] = (),
    *,
    max_queries: int = 4,
    unresolved: bool = False,
    key_conclusion: bool = False,
    one_sided_support: bool = False,
    prompt_version: str = PROMPT_VERSION,
) -> AdversarialPlan:
    """Build bounded counterevidence queries without declaring a claim false."""

    if not 1 <= max_queries <= 8:
        raise ValueError("max_queries must be between 1 and 8")
    statement = _claim_statement(claim)
    materiality = _claim_materiality(claim)
    eligible = is_adversarial_eligible(
        claim,
        unresolved=unresolved,
        key_conclusion=key_conclusion,
        one_sided_support=one_sided_support,
    )
    if not eligible:
        return AdversarialPlan(
            prompt_version=prompt_version,
            claim_id=_claim_id(claim),
            claim=statement,
            materiality=materiality,
            queries=[],
            max_queries=max_queries,
            eligible=False,
            eligibility_reason=(
                "Only high-materiality, key-conclusion, unresolved, or one-sided "
                "claims enter the adversarial lane."
            ),
        )

    requested = _focus_order(evidence_gaps)
    queries = [_query_for(focus, statement) for focus in requested[:max_queries]]
    return AdversarialPlan(
        prompt_version=prompt_version,
        claim_id=_claim_id(claim),
        claim=statement,
        materiality=materiality,
        queries=queries,
        max_queries=max_queries,
        eligible=True,
        eligibility_reason="Claim is eligible for bounded adversarial counterevidence search.",
    )


def normalize_adversarial_result(
    value: Mapping[str, Any],
    *,
    prompt_version: str = PROMPT_VERSION,
    model_version: str = "fixture-adversarial-v1",
) -> AdversarialResult:
    """Validate result evidence and force the non-authoritative boundary."""

    payload = dict(value)
    for forbidden in ("verdict", "claim_verdict", "final_verdict", "authoritative_truth"):
        payload.pop(forbidden, None)
    payload["prompt_version"] = prompt_version
    payload["model_version"] = model_version
    payload["authoritative"] = False
    payload["verdict"] = None
    return AdversarialResult.model_validate(payload)


def record_adversarial_result(
    value: Mapping[str, Any],
    *,
    prompt_version: str = PROMPT_VERSION,
    model_version: str = "fixture-adversarial-v1",
) -> AdversarialResult:
    return normalize_adversarial_result(
        value, prompt_version=prompt_version, model_version=model_version
    )


def _query_for(focus: AdversarialFocus, claim: str) -> AdversarialQuery:
    lead = "Find public evidence that could weaken, contradict, qualify, or supersede this claim"
    suffix = {
        AdversarialFocus.CONTRADICTION: " for explicit contradiction and credible counterevidence",
        AdversarialFocus.NEWER_EVIDENCE: " in newer filings, reporting, or disclosures",
        AdversarialFocus.DEFINITION_CHANGE: " through narrower or broader metric definitions",
        AdversarialFocus.MARKET_EXIT: " through market exits or declines and reduced footprint",
        AdversarialFocus.REGULATORY_ACTION: (
            " through regulatory actions by government or regulators"
        ),
        AdversarialFocus.RESTATEMENT: " through restatements or corrected filings",
        AdversarialFocus.ALTERNATIVE_ESTIMATE: (
            " through alternative estimates from independent research"
        ),
        AdversarialFocus.COUNTEREXAMPLE: " through credible counterexamples",
    }[focus]
    source_types = {
        AdversarialFocus.CONTRADICTION: ["REGULATORY_FILING", "INDEPENDENT_NEWS"],
        AdversarialFocus.NEWER_EVIDENCE: ["REGULATORY_FILING", "INDEPENDENT_NEWS"],
        AdversarialFocus.DEFINITION_CHANGE: ["REGULATORY_FILING", "COMPANY_DISCLOSURE"],
        AdversarialFocus.MARKET_EXIT: ["REGULATORY_FILING", "INDEPENDENT_NEWS"],
        AdversarialFocus.REGULATORY_ACTION: ["GOVERNMENT_REGULATOR", "REGULATORY_FILING"],
        AdversarialFocus.RESTATEMENT: ["REGULATORY_FILING", "AUDIT_REPORT"],
        AdversarialFocus.ALTERNATIVE_ESTIMATE: ["INDEPENDENT_RESEARCH", "INDEPENDENT_NEWS"],
        AdversarialFocus.COUNTEREXAMPLE: ["INDEPENDENT_NEWS", "GOVERNMENT_REGULATOR"],
    }[focus]
    return AdversarialQuery(
        focus=focus,
        intent=f"{lead}{suffix}.",
        query=f'{lead}{suffix}: "{claim}"',
        preferred_source_types=source_types,
    )


def _focus_order(evidence_gaps: Iterable[str]) -> list[AdversarialFocus]:
    order = list(AdversarialFocus)
    text = " ".join(str(gap).casefold() for gap in evidence_gaps)
    priorities: list[AdversarialFocus] = []
    keywords = (
        (AdversarialFocus.NEWER_EVIDENCE, ("new", "stale", "recent")),
        (AdversarialFocus.DEFINITION_CHANGE, ("definition", "method", "scope")),
        (AdversarialFocus.MARKET_EXIT, ("exit", "decline", "market")),
        (AdversarialFocus.REGULATORY_ACTION, ("regulator", "legal", "action")),
        (AdversarialFocus.RESTATEMENT, ("restat", "corrected", "filing")),
        (AdversarialFocus.ALTERNATIVE_ESTIMATE, ("estimate", "range", "alternative")),
        (AdversarialFocus.COUNTEREXAMPLE, ("counterexample", "counter-example")),
    )
    for focus, terms in keywords:
        if any(term in text for term in terms):
            priorities.append(focus)
    return priorities + [focus for focus in order if focus not in priorities]


class AdversarialQueryPlanner:
    """Small façade returning bounded, inspectable counterevidence queries."""

    def __init__(self, *, max_queries: int = 8, prompt_version: str = PROMPT_VERSION) -> None:
        if not 1 <= max_queries <= 8:
            raise ValueError("max_queries must be between 1 and 8")
        self.max_queries = max_queries
        self.prompt_version = prompt_version

    def plan(
        self,
        claim: Mapping[str, Any] | str,
        evidence_gaps: Iterable[str] = (),
        *,
        unresolved: bool = False,
        key_conclusion: bool = False,
        one_sided_support: bool = False,
    ) -> list[AdversarialQuery]:
        result = build_adversarial_plan(
            claim,
            evidence_gaps,
            max_queries=self.max_queries,
            unresolved=unresolved,
            key_conclusion=key_conclusion,
            one_sided_support=one_sided_support,
            prompt_version=self.prompt_version,
        )
        return result.queries


def _claim_statement(claim: Mapping[str, Any] | str) -> str:
    if isinstance(claim, str):
        statement = claim.strip()
    else:
        statement = str(claim.get("statement") or claim.get("claim") or "").strip()
    if not statement:
        raise ValueError("claim statement is required")
    return statement


def _claim_materiality(claim: Mapping[str, Any] | str) -> str:
    if isinstance(claim, str):
        return "HIGH"
    return str(claim.get("materiality") or "MEDIUM").strip().upper()


def _claim_id(claim: Mapping[str, Any] | str) -> str | None:
    if isinstance(claim, str):
        return None
    value = claim.get("claim_id") or claim.get("id") or ""
    return str(value) or None


# Friendly names retained for earlier callers.
AdversarialSearchPlan = AdversarialPlan
AdversarialSearchResult = AdversarialResult
plan_adversarial_search = build_adversarial_plan


__all__ = [
    "AdversarialEvidence",
    "AdversarialFocus",
    "AdversarialOutcome",
    "AdversarialPlan",
    "AdversarialQuery",
    "AdversarialResult",
    "AdversarialQueryPlanner",
    "AdversarialSearchPlan",
    "AdversarialSearchResult",
    "PROMPT_VERSION",
    "SCHEMA_VERSION",
    "build_adversarial_plan",
    "is_adversarial_eligible",
    "normalize_adversarial_result",
    "plan_adversarial_search",
    "record_adversarial_result",
]
