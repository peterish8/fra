"""Fixture-backed canonical verdict and publication-gate contracts."""

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
        f"missing verdict/publication contract: {module_name}.{name} ({error})",
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
    pytest.fail("verdict/publication contract returned a non-object result", pytrace=False)


@pytest.mark.parametrize(
    "case",
    _cases()["verdict_cases"],
    ids=lambda case: case["id"],
)
def test_canonical_verdict_engine_distinguishes_all_evidence_states(case: dict[str, Any]) -> None:
    input_type = _symbol("app.domain.verification.verdicts", "VerdictInput")
    determine = _symbol("app.domain.verification.verdicts", "determine_verdict")
    semantic_type = _symbol(
        "app.domain.verification.semantic", "SemanticOutcome"
    )
    numeric_passed = (
        None if case["numeric_check"] == "NOT_APPLICABLE" else case["numeric_check"] == "PASS"
    )
    temporal_passed = (
        None
        if case["temporal_check"] == "NOT_APPLICABLE"
        else case["temporal_check"] == "PASS"
    )
    value = input_type(
        semantic_outcomes=[semantic_type(case["verification_outcome"])],
        has_evidence=case["verification_outcome"] != "INSUFFICIENT",
        has_independent_evidence=case["independent_evidence"],
        critical_conflict=case["critical_conflict"],
        identity_passed=case["identity_complete"],
        numeric_passed=numeric_passed,
        temporal_passed=temporal_passed,
        freshness=case["freshness"],
    )
    result = determine(value)
    verdict = _mapping(result).get("verdict", result if isinstance(result, str) else None)

    assert verdict == case["expected_verdict"]


@pytest.mark.parametrize(
    "case",
    _cases()["publication_cases"],
    ids=lambda case: case["id"],
)
def test_publication_gate_exposes_each_blocker_and_ready_quality_state(
    case: dict[str, Any],
) -> None:
    gate_type = _symbol(
        "app.domain.reports.publication", "PublicationGateInput"
    )
    evaluate = _symbol(
        "app.domain.reports.publication",
        "evaluate_publication_gate",
        "check_publication_gate",
    )
    if case["id"] == "temporal_blocker":
        assert "temporal_passed" in gate_type.model_fields, (
            "publication gate must expose a temporal validation input"
        )
        return

    claim_ids = [
        "11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222",
        "33333333-3333-4333-8333-333333333333",
        "44444444-4444-4444-8444-444444444444",
    ]
    citation_count = round(len(claim_ids) * case["citation_coverage"])
    synthesis = {
        "sections": [
            {
                "key": "financials",
                "paragraphs": [
                    {
                        "text": "Revenue increased.",
                        "claim_version_ids": []
                        if case["unmapped_facts"]
                        else claim_ids[:1],
                    }
                ],
            }
        ]
    }
    value = gate_type(
        claim_version_ids=claim_ids,
        citation_verified_ids=claim_ids[:citation_count],
        blocking_claim_ids=[] if case["expected_allowed"] else [claim_ids[0]],
        critical_conflicts=int(case["critical_conflict"]),
        identity_passed=case["identity_complete"],
        numeric_passed=case["numeric_check"] == "PASS",
        score_version=case["score_version"],
        prompt_version=case["prompt_version"],
        config_version=case["config_version"],
        synthesis=synthesis,
    )
    result = evaluate(value)
    result_map = _mapping(result)

    assert result_map["passed"] is case["expected_allowed"]
    assert result_map["report_status"] == case["expected_quality_state"]
    if not case["expected_allowed"]:
        reasons = " ".join(result_map["reasons"]).casefold()
        expected_terms = {
            "CITATION_COVERAGE": ("citation", "coverage"),
            "IDENTITY": ("identity",),
            "CRITICAL_CONFLICT": ("critical conflict",),
            "NUMERIC": ("numeric",),
            "VERSION": ("version",),
            "UNMAPPED_FACT": ("synthesis", "mapped"),
        }[case["expected_blocker"]]
        assert all(term in reasons for term in expected_terms)
        assert result_map["blocking_claims"] >= 1


def test_unmapped_synthesis_facts_are_rejected_before_verified_publication() -> None:
    validate = _symbol(
        "app.domain.reports.publication",
        "validate_synthesis_claim_mapping",
        "validate_synthesis_mapping",
        "check_synthesis_mapping",
    )

    synthesis = {
        "sections": [
            {
                "key": "financials",
                "paragraphs": [
                    {"text": "Revenue doubled last year.", "claim_version_ids": []}
                ],
            }
        ]
    }
    result = validate(
        synthesis,
        allowed_claim_version_ids={"11111111-1111-4111-8111-111111111111"},
    )
    if isinstance(result, list):
        assert "Revenue doubled last year." in result
    else:
        assert result is False
