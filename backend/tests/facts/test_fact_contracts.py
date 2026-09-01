"""Fixture-backed contracts for typed financial facts."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest
from pydantic import BaseModel

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "llm_claim_fact_cases.json"


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
    pytest.fail(f"missing typed fact contract: {module_name}.{name} ({error})", pytrace=False)


def _validate(target: Any, payload: Any) -> Any:
    if isinstance(target, type) and issubclass(target, BaseModel):
        return target.model_validate(payload)
    return target(payload)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    pytest.fail("typed fact output was not an object", pytrace=False)


def _fact_contract() -> Any:
    return _symbol(
        "app.providers.llm.contracts",
        "FinancialFactExtraction",
        "FactExtractionEnvelope",
        "FinancialFactEnvelope",
    )


@pytest.mark.parametrize(
    "case",
    _cases()["financial_facts"],
    ids=lambda case: case["id"],
)
def test_financial_fact_contract_preserves_raw_values_and_unknowns(case: dict[str, Any]) -> None:
    result = _mapping(_validate(_fact_contract(), case["payload"]))
    fact = result["facts"][0]

    assert result["schema_version"] == "llm-extraction-v1"
    assert result["prompt_version"] == "extraction-v1"
    assert fact["raw_value_text"] == case["payload"]["facts"][0]["raw_value_text"]
    assert fact["numeric_value"] == case["expected_numeric_value"]
    if "expected_unit" in case:
        assert fact["unit"] == case["expected_unit"]
    if "expected_text_value" in case:
        assert fact["text_value"] == case["expected_text_value"]
        assert fact["numeric_value"] != 0


def test_evidence_relation_preserves_snapshot_role_directness_and_independence() -> None:
    relation = _symbol(
        "app.domain.claims.models",
        "ClaimEvidence",
        "EvidenceRelation",
        "EvidenceRelationRecord",
    )
    case = _cases()["evidence_relation"]
    result = relation.model_validate(case)
    result_map = result.model_dump()

    assert str(result_map["claim_version_id"]) == case["claim_version_id"]
    assert str(result_map["source_snapshot_id"]) == case["source_snapshot_id"]
    assert result_map["evidence_role"] == case["evidence_role"]
    assert result_map["excerpt"] == case["excerpt"]
    assert result_map["locator"] == case["locator"]
    assert result_map["directness"] == case["directness"]
    assert result_map["is_independent"] is True


@pytest.mark.parametrize("model_name", ["FactInput", "FactRecord"])
def test_fact_numeric_value_rejects_boolean_input(model_name: str) -> None:
    model = _symbol("app.domain.facts.models", model_name)

    with pytest.raises((ValueError, TypeError)):
        model.model_validate(
            {
                "source_snapshot_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "fact_type": "FINANCIAL_METRIC",
                "numeric_value": True,
            }
        )
