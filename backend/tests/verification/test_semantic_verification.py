"""Fixture-backed semantic citation verification contracts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "verification_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _symbol(module_name: str, *names: str) -> Any:
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        _missing(module_name, " or ".join(names), error)
    for name in names:
        if hasattr(module, name):
            return getattr(module, name)
    _missing(module_name, " or ".join(names), AttributeError("none found"))


def _missing(module_name: str, name: str, error: BaseException) -> NoReturn:
    pytest.fail(
        f"missing semantic verification contract: {module_name}.{name} ({error})",
        pytrace=False,
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dumped
    pytest.fail("semantic verifier returned a non-object result", pytrace=False)


@pytest.mark.parametrize(
    "case",
    _cases()["semantic_cases"],
    ids=lambda case: case["id"],
)
def test_semantic_verifier_returns_labeled_outcome_from_claim_evidence_pair(
    case: dict[str, Any],
) -> None:
    request_type = _symbol(
        "app.domain.verification.semantic", "SemanticVerificationRequest"
    )
    verify = _symbol("app.domain.verification.semantic", "verify_semantic")
    claim = case["claim"]
    evidence = case["evidence"]
    request = request_type(
        claim_text=claim["statement"],
        structured_value=claim.get("structured_value", {}),
        evidence_excerpt=evidence.get("excerpt"),
        evidence_context=evidence.get("context"),
        source_metadata={"source_type": evidence.get("source_type")},
    )
    result = verify(request)
    result_map = _mapping(result)

    assert result_map["outcome"] == case["expected_outcome"]
    assert result_map["support_type"] == case["expected_support_type"]
    assert set(result_map["supported_fields"]) == set(case["expected_supported_fields"])
    assert set(result_map["unsupported_fields"]) == set(case["expected_unsupported_fields"])
    assert result_map["reason"]
    assert result_map["model_name"]
    assert result_map["prompt_version"]
    assert result_map["schema_version"]


def test_semantic_verifier_has_no_outside_knowledge_rescue_path() -> None:
    request_type = _symbol(
        "app.domain.verification.semantic", "SemanticVerificationRequest"
    )
    verify = _symbol("app.domain.verification.semantic", "verify_semantic")
    case = next(
        case
        for case in _cases()["semantic_cases"]
        if case["id"] == "outside_knowledge_cannot_rescue"
    )

    request = request_type(
        claim_text=case["claim"]["statement"],
        structured_value=case["claim"].get("structured_value", {}),
        evidence_excerpt=case["evidence"].get("excerpt"),
        evidence_context=case["evidence"].get("context"),
        source_metadata={"source_type": case["evidence"].get("source_type")},
    )
    result = verify(request)

    assert _mapping(result)["outcome"] == "INSUFFICIENT"
