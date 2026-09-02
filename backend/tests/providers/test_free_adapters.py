"""Contract tests for the keyless public-data adapters."""

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request

from app.providers.contracts import ProviderStatus
from app.providers.financial.adapters import SECCompanyFactsHttpAdapter
from app.providers.registries.gleif import GLEIFHttpAdapter


def test_sec_company_facts_uses_descriptive_user_agent_and_normalizes_facts() -> None:
    requests: list[Request] = []

    def transport(request: Request, timeout: float) -> bytes:
        requests.append(request)
        assert timeout == 2.0
        return json.dumps(
            {
                "facts": {
                    "us-gaap": {
                        "Revenues": {
                            "units": {
                                "USD": [
                                    {"val": 1234, "fy": 2025, "fp": "FY", "filed": "2026-02-01"}
                                ]
                            }
                        }
                    }
                }
            }
        ).encode()

    result = SECCompanyFactsHttpAdapter(
        user_agent="Financial Research Agent research@example.com",
        timeout_seconds=2.0,
        transport=transport,
    ).fetch({"cik": "320193"})

    assert result.status is ProviderStatus.SUCCESS
    assert result.provider == "SEC"
    assert result.facts[0].metric == "revenue"
    assert result.facts[0].official is True
    assert result.facts[0].period == "FY2025"
    assert requests[0].full_url.endswith("/api/xbrl/companyfacts/CIK0000320193.json")
    assert requests[0].get_header("User-agent") == (
        "Financial Research Agent research@example.com"
    )


def test_sec_company_facts_maps_rate_limits_without_leaking_response() -> None:
    def transport(request: Request, timeout: float) -> bytes:
        del request, timeout
        raise HTTPError("https://data.sec.gov", 429, "rate limited", {}, None)

    result = SECCompanyFactsHttpAdapter(
        user_agent="Financial Research Agent research@example.com", transport=transport
    ).fetch({"cik": "320193"})

    assert result.status is ProviderStatus.RATE_LIMITED
    assert result.retryable is True
    assert result.error_code == "RATE_LIMITED"
    assert "rate limited" not in (result.reason or "")


def test_gleif_direct_lookup_normalizes_legal_identity() -> None:
    def transport(request: Request, timeout: float) -> bytes:
        assert timeout == 2.0
        assert request.full_url.endswith("/lei-records/5493001KJTIIGC8Y1R12")
        return json.dumps(
            {
                "data": {
                    "id": "5493001KJTIIGC8Y1R12",
                    "attributes": {
                        "entity": {
                            "legalName": {"name": "Example Holdings Ltd"},
                            "legalAddress": {"country": "GB"},
                        },
                        "registration": {
                            "status": "ACTIVE",
                            "initialRegistrationDate": "2012-03-04",
                        },
                    },
                }
            }
        ).encode()

    result = GLEIFHttpAdapter(timeout_seconds=2.0, transport=transport).resolve(
        {"lei": "5493001KJTIIGC8Y1R12"}
    )

    assert result.status == "SUCCESS"
    assert result.legal_record is not None
    assert result.legal_record.legal_name == "Example Holdings Ltd"
    assert result.legal_record.registration_number == "5493001KJTIIGC8Y1R12"
    assert result.legal_record.jurisdiction == "GB"
    assert result.legal_record.legal_status == "ACTIVE"


def test_gleif_invalid_lei_abstains_without_network() -> None:
    called = False

    def transport(request: Request, timeout: float) -> bytes:
        nonlocal called
        called = True
        del request, timeout
        return b"{}"

    result = GLEIFHttpAdapter(transport=transport).resolve({"lei": "not-a-lei"})

    assert result.status == "LEGAL_ENTITY_UNCONFIRMED"
    assert result.legal_record is None
    assert called is False
