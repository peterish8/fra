"""Official-first financial provider and fallback outcome contracts."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "financial_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _symbol(*names: str) -> Any:
    for module_name in (
        "app.providers.financial",
        "app.providers.financial.adapters",
        "app.domain.financial.providers",
    ):
        try:
            module = import_module(module_name)
        except ModuleNotFoundError:
            continue
        for name in names:
            if hasattr(module, name):
                return getattr(module, name)
    _missing(" or ".join(names))


def _missing(name: str) -> NoReturn:
    pytest.fail(f"missing financial provider contract: {name}", pytrace=False)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump()
    pytest.fail("financial provider returned a non-object result", pytrace=False)


@pytest.mark.parametrize("case", _cases()["provider_cases"], ids=lambda case: case["id"])
def test_official_first_fallback_status_and_lineage_are_normalized(case: dict[str, Any]) -> None:
    adapter_type = _symbol("FixtureFinancialAdapter")
    official_type = _symbol("OfficialFilingAdapter")
    router_type = _symbol("FinancialProviderRouter")
    status_type = _symbol("ProviderStatus")
    payload = {
        "facts": [
            {
                "metric": "revenue",
                "value": 100 if case["id"] != "provider_disagreement_is_preserved" else 100,
                "unit": "million",
                "currency": "USD",
                "period": "FY2026",
            }
        ]
    }
    official_payload = payload
    fallback_payload = {
        "facts": [{"metric": "revenue", "value": 200, "unit": "million", "currency": "USD"}]
    }
    if case["id"] == "malformed_payload_is_not_fact":
        official_payload = {"facts": "not-a-list"}
    status_values = {
        "TIMEOUT": "TEMPORARY_FAILURE",
        "MALFORMED": "SUCCESS",
        "SUCCESS_DIFFERENT_VALUE": "SUCCESS",
    }
    official = official_type(
        official_payload,
        status=status_type(status_values.get(case["official_status"], case["official_status"])),
    )
    fallback = adapter_type(
        fallback_payload if case["id"] == "provider_disagreement_is_preserved" else payload,
        provider="FALLBACK",
        status=status_type(status_values.get(case["fallback_status"], case["fallback_status"])),
    )
    if case["id"] == "malformed_payload_is_not_fact":
        output = _mapping(official.fetch({"ticker": "ACME"}))
        assert str(output["status"]) == "PARSE_FAILED"
        assert output["facts"] == []
        return
    result = router_type(official, [fallback]).fetch({"ticker": "ACME"})
    output = _mapping(result)
    expected_status = {
        "SUCCESS": "SUCCESS",
        "NO_RESULTS": "NO_RESULTS",
        "TIMEOUT": "TEMPORARY_FAILURE",
        "RATE_LIMITED": "RATE_LIMITED",
        "MALFORMED": "PARSE_FAILED",
        "SUCCESS_DIFFERENT_VALUE": "SUCCESS",
    }
    if case["id"] == "provider_disagreement_is_preserved":
        assert output.get("provider") == "OFFICIAL_FILING"
        assert output.get("safe_metadata", {}).get("disagreement")
        assert output["facts"][0]["normalized_value"] != 150000000
        return
    expected_status_value = expected_status[case["official_status"]]
    if case["expected_provider"] == "FALLBACK":
        expected_status_value = "SUCCESS"
    assert str(output.get("status")) == expected_status_value
    if case["expected_provider"] is not None:
        assert output.get("provider") == {
            "OFFICIAL": "OFFICIAL_FILING",
            "FALLBACK": "FALLBACK",
        }[case["expected_provider"]]
    assert output.get("retrieved_at")
    assert output.get("latency_ms") is not None
    assert output.get("cost_usd_estimate") is not None
