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
    # Keep both names in the serialized contract.  ``model_name`` was the
    # original API spelling and remains useful to consumers that persist the
    # verifier result as JSON.
    model_name: str
    prompt_version: str
    schema_version: str


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
            unsupported_fields=_unsupported_field_names(
                request.claim_text, request.structured_value
            ),
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
            unsupported_fields=_unsupported_field_names(
                request.claim_text, request.structured_value
            ),
        )

    supported, unsupported, numeric_contradiction = _field_support(
        request.claim_text, request.structured_value, evidence
    )
    # A structured claim is verified field-by-field.  Lexical overlap alone is
    # not enough: it would mark an unrelated sentence as support merely because
    # it repeats the company name or a reporting period.
    if numeric_contradiction:
        return _result(
            request,
            SemanticOutcome.FAIL,
            SupportType.CONTRADICTS,
            "The supplied evidence contains a different value for a comparable claim field.",
            supported_fields=[],
            unsupported_fields=unsupported,
        )
    if supported and not unsupported:
        return _result(
            request,
            SemanticOutcome.PASS,
            SupportType.DIRECT,
            "The supplied evidence directly supports every claim field supplied.",
            supported_fields=supported,
            unsupported_fields=[],
        )
    if supported:
        return _result(
            request,
            SemanticOutcome.PARTIAL,
            SupportType.DIRECT,
            "The supplied evidence directly supports only part of the claim.",
            supported_fields=supported,
            unsupported_fields=unsupported,
        )
    return _result(
        request,
        SemanticOutcome.INSUFFICIENT,
        SupportType.NONE,
        "The supplied evidence does not establish the claim from the provided context.",
        supported_fields=[],
        unsupported_fields=unsupported,
    )


def _result(
    request: SemanticVerificationRequest,
    outcome: SemanticOutcome,
    support_type: SupportType,
    reason: str,
    *,
    supported_fields: list[str] | None = None,
    unsupported_fields: list[str] | None = None,
) -> SemanticVerificationResult:
    return SemanticVerificationResult(
        outcome=outcome,
        support_type=support_type,
        reason=reason,
        supported_fields=supported_fields or [],
        unsupported_fields=unsupported_fields or [],
        model_version=request.model_name,
        model_name=request.model_name,
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

    def verify(
        self, *, claim: dict[str, Any], evidence: dict[str, Any]
    ) -> SemanticVerificationResult:
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
        return verify_semantic(request)


def _field_support(
    statement: str, structured: dict[str, Any], evidence: str
) -> tuple[list[str], list[str], bool]:
    """Compare explicit structured fields with supplied evidence text."""

    haystack = evidence.casefold()
    if not statement.strip() or not evidence.strip():
        return [], list(_claim_fields(statement, structured)), False
    fields = _claim_fields(statement, structured)
    supported: list[str] = []
    unsupported: list[str] = []
    contradiction = False
    for field, value in fields.items():
        key = field.replace("_", " ").casefold()
        if _value_in_evidence(field, value, haystack):
            supported.append(field)
        elif key in haystack and isinstance(value, (int, float, str)):
            supported.append(field)
        else:
            unsupported.append(field)
        if (
            field in {"value", "amount"}
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            if _has_comparable_metric(fields, haystack) and _numeric_value_conflicts(
                value, haystack
            ):
                contradiction = True
                if field in supported:
                    supported.remove(field)
                if field not in unsupported:
                    unsupported.append(field)
    return supported, unsupported, contradiction


def _claim_fields(statement: str, structured: dict[str, Any]) -> dict[str, Any]:
    if structured:
        fields = {
            str(key): value
            for key, value in structured.items()
            if key not in {"operator"} and value is not None
        }
        # Qualitative metric objects use ``metric`` as the field name and
        # ``value`` as its label (for example market_position=leader).  Expose
        # those canonical fields rather than reporting an opaque generic value.
        metric = fields.get("metric")
        if isinstance(metric, str) and not isinstance(fields.get("value"), (int, float)):
            qualitative_value = fields.get("value")
            fields.pop("metric", None)
            fields.pop("value", None)
            fields[metric] = qualitative_value or metric
        return fields
    lowered = statement.casefold()
    if "profitable" in lowered:
        return {"profitability": "profitable"}
    return {"statement": statement}


def _numbers_differ(token: str, expected: int | float) -> bool:
    try:
        return float(token.replace(",", "")) != float(expected)
    except ValueError:
        return False


def _unsupported_field_names(statement: str, structured: dict[str, Any]) -> list[str]:
    return list(_claim_fields(statement, structured))


def _value_in_evidence(field: str, value: Any, evidence: str) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return str(value).casefold() in evidence
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _numeric_value_present(value, evidence)
    label = str(value).casefold()
    if label in evidence:
        return True
    if field in {"currency", "currency_code"}:
        symbols = {"usd": "$", "eur": "€", "gbp": "£", "inr": "₹"}
        symbol = symbols.get(label)
        return bool(symbol and symbol in evidence)
    return False


def _numeric_value_present(expected: int | float, evidence: str) -> bool:
    for token, scale in _numeric_observations(evidence):
        if token * scale == float(expected):
            return True
    return False


def _numeric_value_conflicts(expected: int | float, evidence: str) -> bool:
    observations = _numeric_observations(evidence)
    return bool(observations) and not any(
        token * scale == float(expected) for token, scale in observations
    )


def _numeric_observations(evidence: str) -> list[tuple[float, float]]:
    observations: list[tuple[float, float]] = []
    pattern = re.compile(
        r"(?:[$€£₹]\s*)?(\d[\d,]*(?:\.\d+)?)\s*(million|billion|trillion|lakh|crore)?",
        re.IGNORECASE,
    )
    for match in pattern.finditer(evidence):
        raw = match.group(1).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        # Period labels (FY2026) are not financial observations.
        if not match.group(2) and 1900 <= value <= 2100:
            continue
        scale_map: dict[str | None, float] = {
            "million": 1.0,
            "billion": 1_000.0,
            "trillion": 1_000_000.0,
            "lakh": 100_000.0,
            "crore": 10_000_000.0,
            None: 1.0,
        }
        scale = scale_map[match.group(2).casefold() if match.group(2) else None]
        observations.append((value, scale))
    return observations


def _has_comparable_metric(fields: dict[str, Any], evidence: str) -> bool:
    for field, value in fields.items():
        if field in {"value", "amount"} or not isinstance(value, str):
            continue
        if value.casefold() in evidence or field.replace("_", " ").casefold() in evidence:
            return True
    return False


__all__ = [
    "SemanticOutcome",
    "SemanticVerificationRequest",
    "SemanticVerificationResult",
    "SemanticVerifier",
    "SupportType",
    "verify_semantic",
]
