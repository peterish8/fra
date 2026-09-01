"""Fixture-only red contracts for registry normalization and relationship history."""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "entity_resolution_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _symbol(module_name: str, name: str) -> Any:
    try:
        module = import_module(module_name)
        return getattr(module, name)
    except (ModuleNotFoundError, AttributeError) as error:
        _missing(module_name, name, error)


def _missing(module_name: str, name: str, error: BaseException) -> NoReturn:
    pytest.fail(
        f"missing registry/relationship behavior: {module_name}.{name} ({error})",
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
    pytest.fail("registry/relationship behavior returned a non-object result", pytrace=False)


def test_registry_success_records_legal_identity_source_retrieval_and_freshness() -> None:
    case = next(item for item in _cases()["registry_cases"] if item["id"] == "official_current")
    normalize = _symbol("app.providers.registries.contracts", "normalize_registry_result")

    result = _mapping(
        normalize(
            provider=case["provider"],
            payload=case["payload"],
            retrieved_at=case["retrieved_at"],
            freshness_policy_days=case["freshness_policy_days"],
        )
    )
    expected = case["expected"]

    assert result["status"] == expected["status"] == "SUCCESS"
    record = result["legal_record"]
    assert record["legal_name"] == expected["legal_name"]
    assert record["registration_number"] == expected["registration_number"]
    assert record["jurisdiction"] == expected["jurisdiction"]
    assert record["legal_status"] == expected["legal_status"]
    assert record["source"] == expected["source"]
    assert record["retrieved_at"] == expected["retrieved_at"]
    assert record["freshness"] == expected["freshness"]


def test_stale_registry_data_is_retained_but_not_presented_as_current() -> None:
    case = next(item for item in _cases()["registry_cases"] if item["id"] == "stale_cached_record")
    normalize = _symbol("app.providers.registries.contracts", "normalize_registry_result")

    result = _mapping(
        normalize(
            provider=case["provider"],
            payload=case["payload"],
            retrieved_at=case["retrieved_at"],
            freshness_policy_days=case["freshness_policy_days"],
            as_of=case["as_of"],
        )
    )
    assert result["status"] == "SUCCESS"
    assert result["legal_record"]["freshness"] == "STALE"
    assert result["legal_record"]["retrieved_at"] == case["retrieved_at"]


@pytest.mark.parametrize(
    "case_id",
    ["no_results", "rate_limited", "access_restricted", "parse_failure"],
)
def test_registry_failures_normalize_to_legal_entity_unconfirmed(case_id: str) -> None:
    case = next(item for item in _cases()["registry_cases"] if item["id"] == case_id)
    normalize = _symbol("app.providers.registries.contracts", "normalize_registry_result")

    result = _mapping(
        normalize(
            provider=case["provider"],
            payload=case["payload"],
            provider_status=case["provider_status"],
            retrieved_at=case["retrieved_at"],
        )
    )
    assert result["status"] == "LEGAL_ENTITY_UNCONFIRMED"
    assert result["legal_record"] is None
    assert result["reason"]


def test_relationship_history_preserves_scope_effective_dates_and_evidence() -> None:
    case = _cases()["relationship_cases"][0]
    normalize = _symbol("app.domain.companies.relationships", "normalize_relationship_history")

    result = normalize(case["relationships"])
    assert len(result) == 4
    assert {item["relationship_type"] for item in result} == {
        "PARENT_SUBSIDIARY",
        "FORMER_NAME",
        "ACQUISITION",
        "MERGER",
    }
    for original, normalized in zip(case["relationships"], result, strict=True):
        assert normalized["from_company_id"] == original["from_company_id"]
        assert normalized["to_company_id"] == original["to_company_id"]
        assert normalized["entity_scope"] == original["entity_scope"]
        assert normalized["effective_from"] == original["effective_from"]
        assert normalized["effective_to"] == original["effective_to"]
        assert normalized["evidence_refs"] == original["evidence_refs"]
