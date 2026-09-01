"""Fixture-backed red contracts for normalized retrieval capabilities."""

from __future__ import annotations

import inspect
import json
from collections.abc import Mapping
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
        f"missing provider contract behavior: {module_name}.{name} ({error})",
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
    pytest.fail("provider contract returned a non-object result", pytrace=False)


def _field(result: Any, *names: str) -> Any:
    dumped = _mapping(result)
    for name in names:
        if name in dumped:
            return dumped[name]
    pytest.fail(f"provider result is missing one of: {', '.join(names)}", pytrace=False)


@pytest.mark.parametrize(
    "case_id",
    [
        "success",
        "no_results",
        "rate_limited",
        "parse_failed",
        "timeout",
        "permanent_failure",
        "access_restricted",
    ],
)
def test_provider_result_normalizes_status_lineage_and_retry_classification(case_id: str) -> None:
    case = next(item for item in _cases()["provider_results"] if item["id"] == case_id)
    normalize = _symbol("app.providers.contracts", "normalize_provider_result")

    result = normalize(
        provider=case["provider"],
        operation=case["operation"],
        payload=case["payload"],
        provider_status=case["status"],
        provider_request_id=case["provider_request_id"],
        retrieved_at=case["retrieved_at"],
        latency_ms=case["latency_ms"],
        cost_usd_estimate=case["cost_usd_estimate"],
        raw_metadata=case["raw_metadata"],
        error_code=case["error_code"],
        retry_classification=case["retry_classification"],
    )
    expected = case["expected"]

    assert _field(result, "status") == case["status"]
    assert (_field(result, "data", "payload") is not None) is expected["data_present"]
    assert _field(result, "provider_request_id", "request_id") == case["provider_request_id"]
    assert _field(result, "retrieved_at") == case["retrieved_at"]
    assert _field(result, "latency_ms") == case["latency_ms"]
    assert str(_field(result, "cost_usd_estimate", "estimated_cost_usd")) == case[
        "cost_usd_estimate"
    ]
    assert _field(result, "error_code") == case["error_code"]
    assert _field(result, "retry_classification", "retryability") == case[
        "retry_classification"
    ]

    metadata = _mapping(_field(result, "safe_metadata", "metadata", "raw_metadata"))
    assert set(expected["metadata_keys"]).issubset(metadata)
    assert all(isinstance(key, str) for key in metadata)


def test_provider_status_contract_contains_all_required_outcomes() -> None:
    status_type = _symbol("app.providers.contracts", "ProviderStatus")
    required = {
        "SUCCESS",
        "NO_RESULTS",
        "RATE_LIMITED",
        "PARSE_FAILED",
        "TIMEOUT",
        "PERMANENT_FAILURE",
        "ACCESS_RESTRICTED",
    }

    values = {getattr(status_type, name, None) for name in required}
    assert None not in values
    assert {str(value) for value in values} == required


def test_normalized_provider_metadata_redacts_tokens_cookies_and_secrets() -> None:
    case = _cases()["secret_metadata"]
    normalize = _symbol("app.providers.contracts", "normalize_provider_result")

    result = normalize(
        provider=case["provider"],
        operation=case["operation"],
        payload=case["payload"],
        provider_status="SUCCESS",
        provider_request_id=case["provider_request_id"],
        retrieved_at=case["retrieved_at"],
        latency_ms=case["latency_ms"],
        cost_usd_estimate=case["cost_usd_estimate"],
        raw_metadata=case["raw_metadata"],
        error_code=None,
        retry_classification="NOT_RETRYABLE",
    )

    serialized = json.dumps(_mapping(result), default=str, sort_keys=True)
    for secret in (
        "fixture-provider-token",
        "fixture-session-cookie",
        "fixture-api-key",
        "fixture-access-token",
        "fixture-nested-secret",
    ):
        assert secret not in serialized
    metadata = _mapping(_field(result, "safe_metadata", "metadata", "raw_metadata"))
    forbidden = {"authorization", "cookie", "api_key", "access_token", "secret"}
    for key, value in metadata.items():
        if key.lower() in forbidden:
            assert value in (None, "[REDACTED]")


def test_capability_interfaces_return_normalized_results_not_provider_payloads() -> None:
    provider_result = _symbol("app.providers.contracts", "ProviderResult")
    for interface_name, method_name in (
        ("SearchCapability", "search"),
        ("ExtractionCapability", "extract"),
    ):
        interface = _symbol("app.providers.contracts", interface_name)
        assert getattr(interface, "_is_protocol", False), f"{interface_name} must be a Protocol"
        method = getattr(interface, method_name, None)
        assert callable(method), f"{interface_name}.{method_name} is missing"
        return_annotation = inspect.signature(method).return_annotation
        assert "ProviderResult" in str(return_annotation)
        assert provider_result is not None


@pytest.mark.parametrize("case", _cases()["restricted_markers"], ids=lambda case: case["id"])
def test_login_paywall_and_captcha_markers_become_access_restricted(case: dict[str, Any]) -> None:
    normalize = _symbol("app.providers.contracts", "normalize_provider_result")

    result = normalize(
        provider="firecrawl",
        operation="extract",
        payload={"text": case["marker"]},
        provider_status="SUCCESS",
        provider_request_id=f"fixture_{case['id']}",
        retrieved_at="2026-09-01T09:00:00Z",
        latency_ms=10,
        cost_usd_estimate="0.0010",
        raw_metadata={"body": case["marker"]},
        error_code=None,
        retry_classification="NOT_RETRYABLE",
    )

    assert _field(result, "status") == case["expected_status"]
    assert _field(result, "data", "payload") is None
