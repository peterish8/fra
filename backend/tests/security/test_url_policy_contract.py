"""Fixture-backed red contracts for safe URL and redirect validation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "ssrf_corpus.json"


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
        f"missing URL policy behavior: {module_name}.{name} ({error})",
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
    pytest.fail("URL policy returned a non-object result", pytrace=False)


def _result_field(result: Any, name: str) -> Any:
    result_map = _mapping(result)
    if name not in result_map:
        pytest.fail(f"URL policy result is missing {name}", pytrace=False)
    return result_map[name]


def _empty_resolver(hostname: str) -> list[str]:
    del hostname
    return []


def _failing_resolver(hostname: str) -> list[str]:
    del hostname
    raise OSError("DNS unavailable")


@pytest.mark.parametrize("case", _cases()["url_cases"], ids=lambda case: case["id"])
def test_url_policy_allows_only_public_http_https_targets(case: dict[str, Any]) -> None:
    validate_url = _symbol("app.security.url_policy", "validate_url")
    resolver_calls: list[str] = []

    def resolver(hostname: str) -> list[str]:
        resolver_calls.append(hostname)
        return case["addresses"]

    result = validate_url(case["url"], resolver=resolver)

    assert _result_field(result, "allowed") is case["expected_allowed"]
    if not case["expected_allowed"]:
        assert case["reason"] in str(
            _result_field(
                result,
                "reason",
            )
        )


@pytest.mark.parametrize(
    "case",
    _cases()["redirect_cases"],
    ids=lambda case: case["id"],
)
def test_redirect_policy_rechecks_each_hop_caps_redirects_and_detects_rebinding(
    case: dict[str, Any],
) -> None:
    validate_redirects = _symbol("app.security.url_policy", "validate_redirect_chain")
    resolver_calls: list[str] = []
    sequences = case.get("resolver_sequences")
    sequence_positions: dict[str, int] = {}

    def resolver(hostname: str) -> list[str]:
        resolver_calls.append(hostname)
        if sequences is not None:
            values = sequences[hostname]
            position = sequence_positions.get(hostname, 0)
            sequence_positions[hostname] = position + 1
            return values[min(position, len(values) - 1)]
        return case["addresses"][hostname]

    kwargs: dict[str, Any] = {"resolver": resolver}
    if "max_redirects" in case:
        kwargs["max_redirects"] = case["max_redirects"]
    result = validate_redirects(case["initial_url"], case["redirects"], **kwargs)

    assert _result_field(result, "allowed") is case["expected_allowed"]
    if not case["expected_allowed"]:
        assert case["reason"] in str(_result_field(result, "reason"))
    if "expected_resolver_calls" in case:
        assert len(resolver_calls) >= case["expected_resolver_calls"]


@pytest.mark.parametrize(
    ("url", "expected_reason"),
    [
        ("https://user:password@public.example.test/report", "INVALID_URL"),
        ("https://public.example.test/report\nnext", "INVALID_URL"),
        ("https://[invalid]/report", "INVALID_URL"),
        ("https://public.example.test:invalid/report", "INVALID_URL"),
    ],
)
def test_url_policy_rejects_ambiguous_or_malformed_urls(
    url: str,
    expected_reason: str,
) -> None:
    validate_url = _symbol("app.security.url_policy", "validate_url")

    result = validate_url(url, resolver=lambda hostname: ["93.184.216.34"])

    assert _result_field(result, "allowed") is False
    assert expected_reason in str(_result_field(result, "reason"))


def test_url_policy_accepts_unicode_path_after_public_dns_validation() -> None:
    validate_url = _symbol("app.security.url_policy", "validate_url")

    result = validate_url(
        "https://public.example.test/reports/résumé",
        resolver=lambda hostname: ["93.184.216.34"],
    )

    assert _result_field(result, "allowed") is True


@pytest.mark.parametrize("resolver", [_empty_resolver, _failing_resolver])
def test_url_policy_fails_closed_when_dns_resolution_is_empty_or_fails(resolver: Any) -> None:
    validate_url = _symbol("app.security.url_policy", "validate_url")

    result = validate_url("https://public.example.test/report", resolver=resolver)

    assert _result_field(result, "allowed") is False
    assert _result_field(result, "reason") == "DNS_RESOLUTION_FAILED"


def test_url_policy_honors_explicit_custom_allowed_port() -> None:
    validate_url = _symbol("app.security.url_policy", "validate_url")

    result = validate_url(
        "https://public.example.test:8443/report",
        resolver=lambda hostname: ["93.184.216.34"],
        allowed_ports={"http": (80,), "https": (443, 8443)},
    )

    assert _result_field(result, "allowed") is True


def test_redirect_policy_anchors_relative_redirects_and_rejects_malformed_targets() -> None:
    validate_redirects = _symbol("app.security.url_policy", "validate_redirect_chain")

    def resolver(hostname: str) -> list[str]:
        return ["93.184.216.34"]

    relative = validate_redirects(
        "https://public.example.test/start",
        ["/final"],
        resolver=resolver,
    )
    malformed = validate_redirects(
        "https://public.example.test/start",
        [None],
        resolver=resolver,
    )

    assert _result_field(relative, "allowed") is True
    assert _result_field(relative, "url") == "https://public.example.test/final"
    assert _result_field(malformed, "allowed") is False
    assert _result_field(malformed, "reason") == "INVALID_URL_REDIRECT"
