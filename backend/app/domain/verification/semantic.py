"""Evidence-bounded semantic verification contracts and deterministic baseline."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.providers.llm.contracts import PROMPT_VERSION, SCHEMA_VERSION


class SemanticOutcome(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    INSUFFICIENT = "INSUFFICIENT"


class SupportType(StrEnum):
    DIRECT = "DIRECT"
    PARTIAL = "PARTIAL"
    # ``CONTRADICTS`` is the public contract spelling.  Keep the longer name
    # as an enum alias for callers from the first draft of this module.
    CONTRADICTS = "CONTRADICTS"
    CONTRADICTORY = "CONTRADICTS"
    NONE = "NONE"


class SemanticVerificationRequest(BaseModel):
    """Only the claim and supplied candidate evidence are accepted."""

    model_config = ConfigDict(extra="forbid")

    claim_text: str = Field(min_length=1, max_length=4_000)
    structured_value: dict[str, Any] = Field(default_factory=dict)
    evidence_excerpt: str | None = Field(default=None, max_length=20_000)
    evidence_context: str | None = Field(default=None, max_length=20_000)
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    model_name: str = "deterministic-baseline"
    prompt_version: str = PROMPT_VERSION
    schema_version: str = SCHEMA_VERSION


class SemanticVerificationResult(BaseModel):
    """Auditable result with no claim about evidence outside the request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: SemanticOutcome
    support_type: SupportType
    reason: str = Field(min_length=1)
    supported_fields: list[str] = Field(default_factory=list)
    unsupported_fields: list[str] = Field(default_factory=list)
    model_version: str
    prompt_version: str
    schema_version: str

    @property
    def model_name(self) -> str:
        """Backward-compatible spelling for the provider/model field."""

        return self.model_version


def verify_semantic(request: SemanticVerificationRequest) -> SemanticVerificationResult:
    """Judge only supplied claim/evidence text using conservative overlap rules."""

    excerpt = (request.evidence_excerpt or "").strip()
    context = (request.evidence_context or "").strip()
    if not excerpt and not context:
        return _result(
            request,
            SemanticOutcome.INSUFFICIENT,
            SupportType.NONE,
            "No candidate evidence was supplied.",
        )
    evidence = f"{excerpt} {context}".strip()
    claim_tokens = _tokens(request.claim_text)
    evidence_tokens = _tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return _result(
            request,
            SemanticOutcome.INSUFFICIENT,
            SupportType.NONE,
            "The supplied claim or evidence has no verifiable terms.",
        )
    overlap = len(claim_tokens & evidence_tokens) / len(claim_tokens)
    contradiction = bool(
        {"not", "no", "never", "denied", "denies", "declined"} & evidence_tokens
    ) and not bool({"not", "no", "never"} & claim_tokens)
    if contradiction and overlap >= 0.45:
        return _result(
            request,
            SemanticOutcome.FAIL,
            SupportType.CONTRADICTS,
            "The supplied evidence uses contradictory wording for overlapping claim terms.",
        )
    if overlap >= 0.8:
        return _result(
            request,
            SemanticOutcome.PASS,
            SupportType.DIRECT,
            "The supplied evidence directly overlaps the claim wording.",
        )
    if overlap >= 0.35:
        return _result(
            request,
            SemanticOutcome.PARTIAL,
            SupportType.PARTIAL,
            "The supplied evidence overlaps only part of the claim wording.",
        )
    return _result(
        request,
        SemanticOutcome.INSUFFICIENT,
        SupportType.NONE,
        "The supplied evidence does not establish the claim from the provided context.",
    )


def _result(
    request: SemanticVerificationRequest,
    outcome: SemanticOutcome,
    support_type: SupportType,
    reason: str,
) -> SemanticVerificationResult:
    return SemanticVerificationResult(
        outcome=outcome,
        support_type=support_type,
        reason=reason,
        model_version=request.model_name,
        prompt_version=request.prompt_version,
        schema_version=request.schema_version,
    )


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 1}


class SemanticVerifier:
    """Small adapter exposing the verifier contract used by workers.

    This adapter intentionally accepts already retrieved evidence only.  It
    does not resolve URLs, call providers, or use world knowledge.
    """

    def __init__(self, *, model_version: str = "deterministic-baseline") -> None:
        self.model_version = model_version

    def verify(self, *, claim: dict[str, Any], evidence: dict[str, Any]) -> SemanticVerificationResult:
        statement = str(claim.get("statement", "")).strip()
        structured = claim.get("structured_value", {})
        if not isinstance(structured, dict):
            structured = {}
        excerpt = str(evidence.get("excerpt", ""))
        context = str(evidence.get("context", ""))
        request = SemanticVerificationRequest(
            claim_text=statement,
            structured_value=structured,
            evidence_excerpt=excerpt,
            evidence_context=context,
            source_metadata={"source_type": evidence.get("source_type")},
            model_name=self.model_version,
        )
        result = verify_semantic(request)
        supported, unsupported, contradiction = _field_support(
            statement, structured, f"{excerpt} {context}"
        )
        if contradiction:
            result = result.model_copy(
                update={
                    "outcome": SemanticOutcome.FAIL,
                    "support_type": SupportType.CONTRADICTS,
                    "supported_fields": [],
                    "unsupported_fields": unsupported,
                }
            )
        elif supported:
            support_type = result.support_type
            if result.outcome is SemanticOutcome.PASS and unsupported:
                result = result.model_copy(update={"outcome": SemanticOutcome.PARTIAL})
            result = result.model_copy(
                update={
                    "support_type": support_type,
                    "supported_fields": supported,
                    "unsupported_fields": unsupported,
                }
            )
        else:
            result = result.model_copy(update={"supported_fields": [], "unsupported_fields": unsupported})
        return result


def _field_support(
    statement: str, structured: dict[str, Any], evidence: str
) -> tuple[list[str], list[str], bool]:
    """Compare explicit structured fields with supplied evidence text."""

    haystack = evidence.casefold()
    if not statement.strip() or not evidence.strip():
        return [], _claim_fields(statement, structured), False
    fields = _claim_fields(statement, structured)
    supported: list[str] = []
    unsupported: list[str] = []
    contradiction = False
    for field, value in fields.items():
        label = str(value).casefold()
        key = field.replace("_", " ").casefold()
        if label and label in haystack:
            supported.append(field)
        elif key in haystack and field in structured and isinstance(value, (int, float, str)):
            supported.append(field)
        else:
            unsupported.append(field)
        if field in {"value", "amount"} and isinstance(value, (int, float)) and not isinstance(value, bool):
            if key in haystack:
                numeric_tokens = re.findall(r"\d+(?:[,.]\d+)*", haystack)
                if numeric_tokens and all(_numbers_differ(token, value) for token in numeric_tokens):
                    contradiction = True
                    if field in supported:
                        supported.remove(field)
                    if field not in unsupported:
                        unsupported.append(field)
    return supported, unsupported, contradiction


def _claim_fields(statement: str, structured: dict[str, Any]) -> dict[str, Any]:
    if structured:
        return {
            str(key): value
            for key, value in structured.items()
            if key not in {"operator"} and value is not None
        }
    lowered = statement.casefold()
    if "profitable" in lowered:
        return {"profitability": "profitable"}
    return {"statement": statement}


def _numbers_differ(token: str, expected: int | float) -> bool:
    try:
        return float(token.replace(",", "")) != float(expected)
    except ValueError:
        return False


__all__ = [
    "SemanticOutcome",
    "SemanticVerificationRequest",
    "SemanticVerificationResult",
    "SemanticVerifier",
    "SupportType",
    "verify_semantic",
]
