"""Fixture-driven official and commercial financial adapters.

Adapters accept payloads supplied by an integration boundary.  They never
perform network access themselves, so production transport, credentials, and
licensing remain explicit infrastructure decisions.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from time import monotonic
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.providers.contracts import ProviderStatus
from app.providers.registries.sec import normalize_sec_company_facts

from .contracts import FinancialProviderResult, normalize_financial_result


class FixtureFinancialAdapter:
    official = False

    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        provider: str,
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
    ) -> None:
        self.payload = payload
        self.provider = provider
        self.status = ProviderStatus(status)

    def fetch(self, query: Mapping[str, str]) -> FinancialProviderResult:
        del query
        return normalize_financial_result(
            provider=self.provider,
            payload=self.payload,
            official=self.official,
            provider_status=self.status,
            source_type="REGULATORY_FILING" if self.official else "FINANCIAL_API",
        )


class OfficialFilingAdapter(FixtureFinancialAdapter):
    official = True

    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        provider: str = "OFFICIAL_FILING",
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
    ) -> None:
        super().__init__(payload, provider=provider, status=status)


class EodhdAdapter(FixtureFinancialAdapter):
    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
    ) -> None:
        super().__init__(payload, provider="EODHD", status=status)


class TwelveDataAdapter(FixtureFinancialAdapter):
    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        status: ProviderStatus | str = ProviderStatus.SUCCESS,
    ) -> None:
        super().__init__(payload, provider="TWELVE_DATA", status=status)


class SECCompanyFactsHttpAdapter:
    """Keyless SEC EDGAR Company Facts adapter.

    EDGAR's ``data.sec.gov`` JSON endpoints do not require an API key.  The
    SEC does require an identifying User-Agent, so callers must provide one
    containing a product name and contact address.  The transport is injected
    for deterministic tests and to keep network policy at the infrastructure
    boundary.
    """

    official = True
    provider = "SEC"

    def __init__(
        self,
        *,
        user_agent: str,
        timeout_seconds: float = 10.0,
        base_url: str = "https://data.sec.gov",
        transport: Callable[[Request, float], bytes] | None = None,
    ) -> None:
        if not user_agent.strip() or "\r" in user_agent or "\n" in user_agent:
            raise ValueError("SEC user_agent must be non-empty and header-safe")
        if timeout_seconds <= 0:
            raise ValueError("SEC timeout_seconds must be positive")
        self.user_agent = user_agent.strip()
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")
        self._transport = transport or _urlopen_bytes

    def fetch(self, query: Mapping[str, str]) -> FinancialProviderResult:
        cik = _normalize_cik(query.get("cik"))
        retrieved_at = datetime.now(UTC)
        if cik is None:
            return FinancialProviderResult(
                provider=self.provider,
                status=ProviderStatus.NO_RESULTS,
                source_type="REGULATORY_FILING",
                retrieved_at=retrieved_at.isoformat(),
                error_code="CIK_REQUIRED",
                reason="SEC Company Facts requires a 10-digit CIK.",
            )

        url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik}.json"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
            method="GET",
        )
        started = monotonic()
        try:
            payload = json.loads(self._transport(request, self.timeout_seconds).decode("utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("SEC response must be an object")
        except HTTPError as error:
            status, error_code, retryable = _sec_http_failure(error.code)
            return _financial_failure(
                status=status,
                error_code=error_code,
                retryable=retryable,
                retrieved_at=retrieved_at,
                latency_ms=(monotonic() - started) * 1000,
            )
        except TimeoutError:
            return _financial_failure(
                status=ProviderStatus.TIMEOUT,
                error_code="UPSTREAM_TIMEOUT",
                retryable=True,
                retrieved_at=retrieved_at,
                latency_ms=(monotonic() - started) * 1000,
            )
        except (URLError, OSError):
            return _financial_failure(
                status=ProviderStatus.TEMPORARY_FAILURE,
                error_code="UPSTREAM_UNAVAILABLE",
                retryable=True,
                retrieved_at=retrieved_at,
                latency_ms=(monotonic() - started) * 1000,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            return _financial_failure(
                status=ProviderStatus.PARSE_FAILED,
                error_code="MALFORMED_SEC_PAYLOAD",
                retryable=False,
                retrieved_at=retrieved_at,
                latency_ms=(monotonic() - started) * 1000,
            )

        result = normalize_sec_company_facts(payload, cik=cik)
        return result.model_copy(
            update={
                "retrieved_at": retrieved_at.isoformat(),
                "latency_ms": (monotonic() - started) * 1000,
                "safe_metadata": {
                    "endpoint": "companyfacts",
                    "cik": cik,
                    "official": True,
                },
            }
        )


class FinancialProviderRouter:
    """Official-first routing with replaceable fallback providers."""

    def __init__(
        self,
        official: FixtureFinancialAdapter | None,
        fallbacks: Sequence[FixtureFinancialAdapter] = (),
    ) -> None:
        self.official = official
        self.fallbacks = tuple(fallbacks)

    def fetch(self, query: Mapping[str, str]) -> FinancialProviderResult:
        providers = ((self.official,) if self.official is not None else ()) + self.fallbacks
        last: FinancialProviderResult | None = None
        for index, provider in enumerate(providers):
            result = provider.fetch(query)
            if result.status is ProviderStatus.SUCCESS:
                # A filing remains the selected observation.  A configured
                # commercial provider can still be a cross-check; never
                # replace or average an official value when it differs.
                if index == 0 and self.official is not None:
                    cross_checks = [fallback.fetch(query) for fallback in self.fallbacks]
                    successful_checks = [
                        candidate
                        for candidate in cross_checks
                        if candidate.status is ProviderStatus.SUCCESS
                    ]
                    if any(_facts_disagree(result, candidate) for candidate in successful_checks):
                        metadata = dict(result.safe_metadata)
                        metadata["disagreement"] = True
                        metadata["cross_check_providers"] = [
                            candidate.provider for candidate in successful_checks
                        ]
                        return result.model_copy(update={"safe_metadata": metadata})
                return result
            last = result
            if result.status in {
                ProviderStatus.ACCESS_RESTRICTED,
                ProviderStatus.PERMANENT_FAILURE,
            }:
                continue
        return last or FinancialProviderResult(
            provider="FINANCIAL_ROUTER",
            status=ProviderStatus.NO_RESULTS,
            reason="No financial provider was configured.",
        )

    retrieve = fetch


def route_financial_facts(
    query: Mapping[str, str],
    *,
    official: FixtureFinancialAdapter | None,
    fallbacks: Sequence[FixtureFinancialAdapter] = (),
) -> FinancialProviderResult:
    return FinancialProviderRouter(official, fallbacks).fetch(query)


def _facts_disagree(primary: FinancialProviderResult, cross_check: FinancialProviderResult) -> bool:
    """Compare like-for-like facts without normalizing away a disagreement."""

    for left in primary.facts:
        for right in cross_check.facts:
            if (
                left.metric == right.metric
                and left.currency == right.currency
                and left.normalized_value != right.normalized_value
            ):
                return True
    return False


def _normalize_cik(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits or len(digits) > 10:
        return None
    return digits.zfill(10)


def _urlopen_bytes(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed SEC URL
        return cast(bytes, response.read())


def _sec_http_failure(code: int) -> tuple[ProviderStatus, str, bool]:
    if code == 429:
        return ProviderStatus.RATE_LIMITED, "RATE_LIMITED", True
    if code in {401, 403}:
        return ProviderStatus.ACCESS_RESTRICTED, "ACCESS_RESTRICTED", False
    if 500 <= code <= 599:
        return ProviderStatus.TEMPORARY_FAILURE, "UPSTREAM_5XX", True
    return ProviderStatus.PERMANENT_FAILURE, f"HTTP_{code}", False


def _financial_failure(
    *,
    status: ProviderStatus,
    error_code: str,
    retryable: bool,
    retrieved_at: datetime,
    latency_ms: float,
) -> FinancialProviderResult:
    return FinancialProviderResult(
        provider="SEC",
        status=status,
        source_type="REGULATORY_FILING",
        retrieved_at=retrieved_at.isoformat(),
        latency_ms=max(0.0, latency_ms),
        error_code=error_code,
        retryable=retryable,
        retry_class="TRANSIENT" if retryable else "NOT_RETRYABLE",
        reason=f"SEC returned {error_code.lower()}.",
    )


__all__ = [
    "EodhdAdapter",
    "FinancialProviderRouter",
    "FixtureFinancialAdapter",
    "OfficialFilingAdapter",
    "SECCompanyFactsHttpAdapter",
    "TwelveDataAdapter",
    "route_financial_facts",
]
