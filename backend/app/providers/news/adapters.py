"""Finnhub company-news adapter.

Finnhub provides a free-tier developer API key for public GET requests. The
key is sent as a query token to this server-side adapter only; it is never
exposed to the browser.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.providers.contracts import ProviderStatus

from .contracts import NewsResult, normalize_news_result


class FinnhubNewsAdapter:
    """Official company-news lookup using a user-owned free API key."""

    provider = "FINNHUB"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 10.0,
        base_url: str = "https://finnhub.io/api/v1",
        transport: Callable[[Request, float], bytes] | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Finnhub api_key must be non-empty")
        if timeout_seconds <= 0:
            raise ValueError("Finnhub timeout_seconds must be positive")
        self._api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")
        self._transport = transport or _urlopen_bytes

    def fetch_company_news(
        self,
        symbol: str,
        *,
        lookback_days: int = 7,
        limit: int = 5,
    ) -> NewsResult:
        normalized_symbol = _normalize_symbol(symbol)
        if normalized_symbol is None:
            return normalize_news_result(
                provider=self.provider,
                payload=None,
                provider_status=ProviderStatus.NO_RESULTS,
            )

        today = datetime.now(UTC).date()
        params = urlencode(
            {
                "symbol": normalized_symbol,
                "from": (today - timedelta(days=max(lookback_days, 1))).isoformat(),
                "to": today.isoformat(),
                "token": self._api_key,
            }
        )
        request = Request(
            f"{self.base_url}/company-news?{params}",
            headers={"Accept": "application/json"},
            method="GET",
        )

        try:
            raw = self._transport(request, self.timeout_seconds).decode("utf-8")
        except HTTPError as error:
            return normalize_news_result(
                provider=self.provider,
                payload=None,
                provider_status=_finnhub_http_status(error.code),
                related_symbol=normalized_symbol,
                limit=limit,
            )
        except (TimeoutError, URLError, OSError):
            return normalize_news_result(
                provider=self.provider,
                payload=None,
                provider_status=ProviderStatus.TEMPORARY_FAILURE,
                related_symbol=normalized_symbol,
                limit=limit,
            )

        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            return normalize_news_result(
                provider=self.provider,
                payload=None,
                provider_status=ProviderStatus.PARSE_FAILED,
                related_symbol=normalized_symbol,
                limit=limit,
            )
        if not isinstance(payload, list):
            return normalize_news_result(
                provider=self.provider,
                payload=None,
                provider_status=ProviderStatus.PARSE_FAILED,
                related_symbol=normalized_symbol,
                limit=limit,
            )

        return normalize_news_result(
            provider=self.provider,
            payload=payload,
            provider_status=ProviderStatus.SUCCESS,
            related_symbol=normalized_symbol,
            limit=limit,
        )


def _normalize_symbol(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip().upper()
    return candidate if re.fullmatch(r"[A-Z0-9.\-]{1,12}", candidate) else None


def _finnhub_http_status(code: int) -> ProviderStatus:
    if code == 404:
        return ProviderStatus.NO_RESULTS
    if code == 429:
        return ProviderStatus.RATE_LIMITED
    if code in {401, 403}:
        return ProviderStatus.ACCESS_RESTRICTED
    if 500 <= code <= 599:
        return ProviderStatus.TEMPORARY_FAILURE
    return ProviderStatus.PERMANENT_FAILURE


def _urlopen_bytes(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed official URL
        return cast(bytes, response.read())


__all__ = ["FinnhubNewsAdapter"]
