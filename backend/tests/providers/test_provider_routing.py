"""Fixture-backed red contracts for health- and cost-aware provider routing."""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "provider_routing_cases.json"


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
        f"missing provider routing behavior: {module_name}.{name} ({error})",
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
    pytest.fail("provider router returned a non-object result", pytrace=False)


def _result_for(normalize: Any, provider: dict[str, Any], operation: str) -> Any:
    payload = {"items": [{"url": "https://evidence.example.test/item"}]}
    if operation == "extract":
        payload = {"text": "Permitted public evidence"}
    return normalize(
        provider=provider["name"],
        operation=operation,
        payload=payload if provider["status"] == "SUCCESS" else None,
        provider_status=provider["status"],
        provider_request_id=f"fixture_{provider['name']}",
        retrieved_at="2026-09-01T09:00:00Z",
        latency_ms=25,
        cost_usd_estimate=provider["cost_usd_estimate"],
        raw_metadata={"fixture": True},
        error_code=None if provider["status"] == "SUCCESS" else provider["status"],
        retry_classification=(
            "NOT_RETRYABLE" if provider["status"] == "SUCCESS" else "RETRYABLE"
        ),
    )


class _FixtureProvider:
    def __init__(self, provider: dict[str, Any], operation: str, normalize: Any) -> None:
        self.provider = provider["name"]
        self.estimated_cost_usd = Decimal(provider["cost_usd_estimate"])
        self._provider = provider
        self._operation = operation
        self._normalize = normalize
        self.calls: list[dict[str, Any]] = []

    def search(self, query: str, **kwargs: Any) -> Any:
        self.calls.append({"query": query, "kwargs": kwargs})
        return _result_for(self._normalize, self._provider, self._operation)

    def extract(self, url: str, **kwargs: Any) -> Any:
        self.calls.append({"url": url, "kwargs": kwargs})
        return _result_for(self._normalize, self._provider, self._operation)


@pytest.mark.parametrize("case", _cases()["routing_cases"], ids=lambda case: case["id"])
def test_router_honors_fallback_order_health_cost_and_restriction_policy(
    case: dict[str, Any],
) -> None:
    normalize = _symbol("app.providers.contracts", "normalize_provider_result")
    router_type = _symbol("app.providers.router", "ProviderRouter")
    operation = case["operation"]
    providers = [_FixtureProvider(item, operation, normalize) for item in case["providers"]]

    router = router_type(
        search_providers=providers if operation == "search" else [],
        extraction_providers=providers if operation == "extract" else [],
        health_state=case["health"],
        remaining_cost_usd=Decimal(case["remaining_budget_usd"]),
    )
    if operation == "search":
        result = router.search(case["query"])
    else:
        result = router.extract(case["url"])

    result_map = _mapping(result)
    assert result_map["status"] == case["expected_status"]
    assert result_map.get("provider", result_map.get("provider_name")) == case[
        "expected_provider"
    ]
    assert [provider.provider for provider in providers if provider.calls] == case[
        "expected_call_order"
    ]

    if operation == "extract" and not case["bypass_attempts_allowed"]:
        for provider in providers:
            for call in provider.calls:
                assert "bypass" not in call["kwargs"]
                assert "captcha" not in call["kwargs"]
                assert "cookie" not in call["kwargs"]
