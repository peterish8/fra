"""Fixture-only red contracts for conservative entity resolution."""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "entity_resolution_cases.json"


def _load_cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _missing_behavior(module_name: str, symbol: str, error: BaseException) -> NoReturn:
    pytest.fail(
        f"missing entity-resolution behavior: {module_name}.{symbol} is not available ({error})",
        pytrace=False,
    )


def _load_symbol(module_name: str, symbol: str) -> Any:
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        _missing_behavior(module_name, symbol, error)
    try:
        return getattr(module, symbol)
    except AttributeError as error:
        _missing_behavior(module_name, symbol, error)


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dumped
    pytest.fail("entity resolution returned a non-object result", pytrace=False)


def _resolve(case: Mapping[str, Any]) -> Mapping[str, Any]:
    resolve_entity = _load_symbol("app.domain.companies.resolver", "resolve_entity")
    return _mapping(resolve_entity(query=case["query"], candidates=case["candidates"]))


@pytest.mark.parametrize(
    "case_id",
    [
        "canonical_name_exact",
        "former_name_alias",
        "ticker_exchange_match",
        "official_domain_match",
        "registry_identifier_match",
    ],
)
def test_supported_identifiers_resolve_to_canonical_company(case_id: str) -> None:
    case = next(item for item in _load_cases()["resolution_cases"] if item["id"] == case_id)
    result = _resolve(case)
    expected = case["expected"]

    assert result["status"] == expected["status"] == "RESOLVED"
    assert result["selected_company_id"] == expected["company_id"]
    assert result["research_allowed"] is True
    selected = next(
        candidate
        for candidate in result["candidates"]
        if candidate["company_id"] == expected["company_id"]
    )
    assert selected["canonical_name"]
    assert 0 <= selected["confidence"] <= 1
    assert selected["confidence"] >= 0.8
    assert any(reason["code"] == expected["reason_code"] for reason in selected["match_reasons"])
    assert selected["evidence_refs"]


def test_jurisdiction_disambiguates_same_name_without_merging_entities() -> None:
    cases = _load_cases()["resolution_cases"]
    selected_case = next(
        item for item in cases if item["id"] == "same_name_jurisdiction_selected"
    )
    ambiguous_case = next(
        item for item in cases if item["id"] == "same_name_without_jurisdiction_ambiguous"
    )

    selected = _resolve(selected_case)
    assert selected["status"] == "RESOLVED"
    assert selected["selected_company_id"] == selected_case["expected"]["company_id"]
    assert {candidate["country_code"] for candidate in selected["candidates"]} == {"IN", "US"}

    ambiguous = _resolve(ambiguous_case)
    assert ambiguous["status"] == "AMBIGUOUS"
    assert ambiguous["selected_company_id"] is None
    assert ambiguous["research_allowed"] is False
    assert len(ambiguous["candidates"]) == 2
    assert all(candidate["company_id"] for candidate in ambiguous["candidates"])
    assert all(candidate["country_code"] in {"IN", "US"} for candidate in ambiguous["candidates"])


@pytest.mark.parametrize(
    "case_id",
    [
        "same_name_without_jurisdiction_ambiguous",
        "sparse_identity_unconfirmed",
        "contradictory_identity_unconfirmed",
        "unverified_copycat_domain_unconfirmed",
    ],
)
def test_resolution_status_is_explicit_and_abstains_when_identity_is_not_safe(case_id: str) -> None:
    case = next(item for item in _load_cases()["resolution_cases"] if item["id"] == case_id)
    result = _resolve(case)
    expected = case["expected"]

    assert result["status"] == expected["status"]
    assert result["status"] in {"AMBIGUOUS", "UNCONFIRMED"}
    assert result["selected_company_id"] is None
    assert result["research_allowed"] is False
    assert result["abstention_reason"]
    assert any(reason["code"] == expected["reason_code"] for reason in result["match_reasons"])


def test_every_candidate_exposes_explainable_confidence_and_evidence_references() -> None:
    result = _resolve(
        next(
            item
            for item in _load_cases()["resolution_cases"]
            if item["id"] == "same_name_without_jurisdiction_ambiguous"
        )
    )

    for candidate in result["candidates"]:
        assert set(candidate) >= {
            "company_id",
            "canonical_name",
            "country_code",
            "entity_type",
            "confidence",
            "match_reasons",
            "evidence_refs",
        }
        assert isinstance(candidate["confidence"], int | float)
        assert 0 <= candidate["confidence"] <= 1
        assert candidate["match_reasons"]
        for reason in candidate["match_reasons"]:
            assert set(reason) >= {"code", "detail"}
            assert reason["code"]
            assert reason["detail"]
        assert candidate["evidence_refs"]


def test_resolution_endpoint_is_authenticated_through_existing_auth_boundary(client: Any) -> None:
    response = client.post(
        "/v1/companies/resolve",
        json={"query": "Meridian Foods"},
        headers={"X-Request-ID": "req_entity_auth_001"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert body["error"]["request_id"] == "req_entity_auth_001"
