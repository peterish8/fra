"""Contract tests for the Finnhub company-news adapter."""

from __future__ import annotations

import json
from email.message import Message
from urllib.error import HTTPError
from urllib.request import Request

from app.providers.news.adapters import FinnhubNewsAdapter


def test_finnhub_news_normalizes_articles_and_sends_token() -> None:
    requests: list[Request] = []

    def transport(request: Request, timeout: float) -> bytes:
        requests.append(request)
        assert timeout == 5.0
        return json.dumps(
            [
                {
                    "headline": "NVIDIA reports record data center revenue",
                    "summary": "Data center segment grew year over year.",
                    "url": "https://example.com/nvidia-earnings",
                    "image": "https://example.com/nvidia.jpg",
                    "source": "Reuters",
                    "datetime": 1_757_000_000,
                },
                {"headline": "", "url": "https://example.com/missing-headline"},
            ]
        ).encode()

    result = FinnhubNewsAdapter(
        api_key="test-key",
        timeout_seconds=5.0,
        transport=transport,
    ).fetch_company_news("nvda", limit=5)

    assert result.status == "SUCCESS"
    assert len(result.items) == 1
    item = result.items[0]
    assert item.headline == "NVIDIA reports record data center revenue"
    assert item.source == "Reuters"
    assert item.related_symbol == "NVDA"
    assert "token=test-key" in requests[0].full_url
    assert "symbol=NVDA" in requests[0].full_url


def test_finnhub_news_maps_rate_limit_without_leaking_response() -> None:
    def transport(request: Request, timeout: float) -> bytes:
        del request, timeout
        raise HTTPError("https://finnhub.io", 429, "rate limited", Message(), None)

    result = FinnhubNewsAdapter(api_key="test-key", transport=transport).fetch_company_news("NVDA")

    assert result.status == "NEWS_UNAVAILABLE"
    assert result.items == []
    assert "rate_limited" in (result.reason or "").lower()


def test_finnhub_news_rejects_invalid_symbol_without_a_network_call() -> None:
    def transport(request: Request, timeout: float) -> bytes:
        del request, timeout
        raise AssertionError("transport must not be called for an invalid symbol")

    result = FinnhubNewsAdapter(api_key="test-key", transport=transport).fetch_company_news(
        "not a symbol!"
    )

    assert result.status == "NEWS_UNAVAILABLE"


def test_finnhub_news_constructor_rejects_blank_api_key() -> None:
    try:
        FinnhubNewsAdapter(api_key="   ")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a blank api_key")
