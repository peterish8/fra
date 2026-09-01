"""Contract tests for the safe public-extraction boundary."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import pytest

from app.providers.contracts import ProviderResult, normalize_provider_result
from app.providers.extraction.safe import SafeExtractionAdapter
from app.providers.router import ProviderRouter

PUBLIC_URL = "https://public.example.test/report"


def _public_resolver(hostname: str) -> list[str]:
    assert hostname == "public.example.test"
    return ["93.184.216.34"]


def _result(
    payload: Any,
    *,
    safe_metadata: Mapping[str, Any] | None = None,
) -> ProviderResult:
    return normalize_provider_result(
        provider="fixture",
        operation="extract",
        payload=payload,
        provider_status="SUCCESS",
        provider_request_id="fixture-request",
        retrieved_at="2026-09-01T09:00:00Z",
        latency_ms=5,
        cost_usd_estimate=Decimal("0.001"),
        raw_metadata=safe_metadata or {},
        error_code=None,
        retry_classification="NOT_RETRYABLE",
    )


class _RecordingAdapter:
    provider = "fixture"
    estimated_cost_usd = Decimal("0.001")

    def __init__(self, result: ProviderResult | None = None, error: BaseException | None = None):
        self.result = result or _result({"text": "public evidence"})
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def extract(self, url: str, **kwargs: Any) -> ProviderResult:
        self.calls.append((url, kwargs))
        if self.error is not None:
            raise self.error
        return self.result


class _RouterProvider:
    def __init__(
        self,
        name: str,
        result: ProviderResult | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.provider = name
        self.estimated_cost_usd = Decimal("0.001")
        self.result = result
        self.error = error
        self.calls: list[str] = []

    def search(self, query: str, **kwargs: Any) -> ProviderResult:
        del kwargs
        self.calls.append(query)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result

    def extract(self, url: str, **kwargs: Any) -> ProviderResult:
        del kwargs
        self.calls.append(url)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _router_result(provider: str, status: str, payload: Any | None = None) -> ProviderResult:
    return normalize_provider_result(
        provider=provider,
        operation="extract",
        payload=payload,
        provider_status=status,
        provider_request_id=f"{provider}-request",
        retrieved_at="2026-09-01T09:00:00Z",
        latency_ms=5,
        cost_usd_estimate=Decimal("0.001"),
        raw_metadata={},
        error_code=None if status == "SUCCESS" else status,
        retry_classification="NOT_RETRYABLE" if status == "SUCCESS" else "RETRYABLE",
    )


@pytest.mark.parametrize(
    "reason",
    ["LOGIN_REQUIRED", "PAYWALL", "CAPTCHA_REQUIRED", "ROBOTS_DISALLOWED"],
)
def test_site_policy_restrictions_stop_extraction_before_adapter_call(reason: str) -> None:
    adapter = _RecordingAdapter()
    safe = SafeExtractionAdapter(
        adapter,
        resolver=_public_resolver,
        site_policy_checker=lambda url: {"allowed": False, "reason": reason},
    )

    result = safe.extract(PUBLIC_URL)

    assert result.status == "ACCESS_RESTRICTED"
    assert result.error_code == reason
    assert result.retry_classification == "NOT_RETRYABLE"
    assert adapter.calls == []


def test_safe_extraction_rejects_ssrf_target_before_site_policy_or_adapter() -> None:
    adapter = _RecordingAdapter()
    policy_calls: list[str] = []
    safe = SafeExtractionAdapter(
        adapter,
        resolver=lambda hostname: ["127.0.0.1"],
        site_policy_checker=lambda url: policy_calls.append(url) or {"allowed": True},
    )

    result = safe.extract("http://attacker.example.test/admin")

    assert result.status == "ACCESS_RESTRICTED"
    assert result.error_code == "LOOPBACK"
    assert policy_calls == []
    assert adapter.calls == []


def test_safe_extraction_passes_bounded_request_settings_and_cannot_be_weakened() -> None:
    adapter = _RecordingAdapter()
    safe = SafeExtractionAdapter(
        adapter,
        resolver=_public_resolver,
        site_policy_checker=lambda url: {"allowed": True},
        timeout_seconds=7.5,
        max_response_bytes=12345,
        max_redirects=2,
    )

    result = safe.extract(
        PUBLIC_URL,
        timeout_seconds=999,
        max_response_bytes=999999,
        max_redirects=99,
        allow_redirects=True,
        follow_redirects=True,
        trace_id="fixture",
    )

    assert result.status == "SUCCESS"
    assert len(adapter.calls) == 1
    _, kwargs = adapter.calls[0]
    assert kwargs == {
        "trace_id": "fixture",
        "timeout_seconds": 7.5,
        "max_response_bytes": 12345,
        "max_redirects": 2,
    }


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (TimeoutError("timed out"), "TIMEOUT"),
        (RuntimeError("provider failed"), "TEMPORARY_FAILURE"),
    ],
)
def test_safe_extraction_adapter_failures_have_correct_retryability(
    error: BaseException,
    expected_status: str,
) -> None:
    adapter = _RecordingAdapter(error=error)
    safe = SafeExtractionAdapter(
        adapter,
        resolver=_public_resolver,
        site_policy_checker=lambda url: {"allowed": True},
    )

    result = safe.extract(PUBLIC_URL)

    assert result.status == expected_status
    assert result.retry_classification == "RETRYABLE"


def test_safe_extraction_rechecks_redirect_chain_after_adapter_returns() -> None:
    adapter = _RecordingAdapter(
        result=_result(
            {"text": "public evidence"},
            safe_metadata={"redirect_chain": ["http://192.168.1.10/private"]},
        )
    )

    def resolver(hostname: str) -> list[str]:
        return {
            "public.example.test": ["93.184.216.34"],
            "192.168.1.10": ["192.168.1.10"],
        }[hostname]

    safe = SafeExtractionAdapter(
        adapter,
        resolver=resolver,
        site_policy_checker=lambda url: {"allowed": True},
        max_redirects=1,
    )

    result = safe.extract(PUBLIC_URL)

    assert result.status == "ACCESS_RESTRICTED"
    assert result.error_code == "PRIVATE_REDIRECT"


def test_provider_router_rechecks_policy_before_each_extraction_adapter() -> None:
    first = _RouterProvider("firecrawl", _router_result("firecrawl", "RATE_LIMITED"))
    second = _RouterProvider(
        "exa_contents",
        _router_result("exa_contents", "SUCCESS", {"text": "public evidence"}),
    )
    policy_calls: list[str] = []

    def validator(url: str) -> dict[str, Any]:
        policy_calls.append(url)
        return {"allowed": True}

    result = ProviderRouter(
        extraction_providers=[first, second],
        url_validator=validator,
    ).extract(PUBLIC_URL)

    assert result.status == "SUCCESS"
    assert policy_calls == [PUBLIC_URL, PUBLIC_URL]
    assert first.calls == [PUBLIC_URL]
    assert second.calls == [PUBLIC_URL]


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [(TimeoutError("timed out"), "TIMEOUT"), (RuntimeError("failed"), "TEMPORARY_FAILURE")],
)
def test_provider_router_adapter_failures_are_retryable(
    error: BaseException,
    expected_status: str,
) -> None:
    result = ProviderRouter(
        search_providers=[_RouterProvider("fixture", error=error)],
    ).search("public evidence")

    assert result.status == expected_status
    assert result.retry_classification == "RETRYABLE"


def test_provider_router_no_healthy_and_no_provider_outcomes_are_retryable() -> None:
    unhealthy = _RouterProvider("fixture", _router_result("fixture", "SUCCESS"))
    no_healthy = ProviderRouter(
        search_providers=[unhealthy],
        health_state={"fixture": "OPEN_CIRCUIT"},
    ).search("public evidence")
    unconfigured = ProviderRouter().search("public evidence")

    assert no_healthy.status == "TEMPORARY_FAILURE"
    assert no_healthy.error_code == "NO_HEALTHY_PROVIDER"
    assert no_healthy.retry_classification == "RETRYABLE"
    assert unconfigured.status == "TEMPORARY_FAILURE"
    assert unconfigured.error_code == "NO_PROVIDER_CONFIGURED"
    assert unconfigured.retry_classification == "RETRYABLE"
