"""Labeled reconciliation contracts for apparent and genuine discrepancies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.domain.verification.conflicts import classify_conflict

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "conflict_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump()
    pytest.fail("reconciliation returned a non-object result", pytrace=False)


@pytest.mark.parametrize(
    "case", _cases()["classification_cases"], ids=lambda case: case["id"]
)
def test_reconciliation_classifies_only_comparable_financial_records(case: dict[str, Any]) -> None:
    result = classify_conflict(case["left"], case["right"])
    output = _mapping(result)
    classification = output.get("classification")
    assert str(classification) == case["expected_classification"]
    if classification not in {"NO_CONFLICT"}:
        assert output.get("severity")
        assert output.get("members")
        assert output.get("explanation")
        assert output.get("status")
    assert output.get("comparability_key")
    if case["expected_classification"] in {
        "DEFINITION_MISMATCH",
        "METHODOLOGY_DIFFERENCE",
        "GAAP_VS_NON_GAAP",
        "PERIOD_MISMATCH",
        "CURRENCY_MISMATCH",
        "ENTITY_SCOPE_DIFFERENCE",
        "SOURCE_DATE_MISMATCH",
    }:
        assert output["comparable"] is False
    if case["expected_classification"] == "VALUE_CONFLICT":
        assert output["comparable"] is True
        assert output["status"] == "OPEN"
    if case["expected_classification"] == "NO_CONFLICT":
        assert output["difference_classification"] == "ROUNDING_DIFFERENCE"
    if case["expected_classification"] in {"NO_CONFLICT", "RESTATEMENT"}:
        assert output["status"] == "RESOLVED"
    assert output.get("average") is None
    assert output.get("midpoint") is None


def test_restatement_preserves_prior_fact_and_links_superseding_fact() -> None:
    case = next(
        case
        for case in _cases()["classification_cases"]
        if case["id"] == "restatement_supersedes_prior"
    )
    result = _mapping(classify_conflict(case["left"], case["right"]))
    assert result.get("classification") == "RESTATEMENT"
    assert set(result["members"]) == {"prior", "restated"}
    assert case["right"]["supersedes_id"] == case["left"]["observation_id"]
    assert result["status"] == "RESOLVED"
    assert (
        "histor" in result["explanation"].lower()
        or "supersed" in result["explanation"].lower()
    )
