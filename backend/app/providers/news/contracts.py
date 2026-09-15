"""Normalized contracts for company-news adapters (the Daily News tab)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.providers.contracts import ProviderStatus


class NewsItem(BaseModel):
    """One normalized headline, independent of which provider supplied it."""

    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=1, max_length=500)
    summary: str | None = None
    url: str = Field(min_length=1)
    image_url: str | None = None
    source: str = Field(min_length=1)
    published_at: str = Field(min_length=1)
    related_symbol: str | None = None


class NewsResult(BaseModel):
    """Explicit outcome: either a list of items, or a reason there are none."""

    status: str
    items: list[NewsItem] = Field(default_factory=list)
    reason: str | None = None


_FAILURE_STATUSES = {
    ProviderStatus.NO_RESULTS.value,
    ProviderStatus.RATE_LIMITED.value,
    ProviderStatus.ACCESS_RESTRICTED.value,
    ProviderStatus.PARSE_FAILED.value,
    ProviderStatus.TEMPORARY_FAILURE.value,
    ProviderStatus.PERMANENT_FAILURE.value,
}


def normalize_news_result(
    *,
    provider: str,
    payload: Sequence[Mapping[str, Any]] | None,
    provider_status: ProviderStatus | str | None,
    related_symbol: str | None = None,
    limit: int = 5,
) -> NewsResult:
    """Normalize a provider's raw article list without inventing missing fields.

    An article missing a headline or URL is dropped rather than guessed at;
    any provider failure becomes an explicit status, never an empty success.
    """

    provider_name = provider.strip().upper()
    status = str(
        provider_status.value
        if isinstance(provider_status, ProviderStatus)
        else provider_status or ""
    ).upper()
    if status in _FAILURE_STATUSES or payload is None:
        reason_code = status or "NO_RESULTS"
        return NewsResult(
            status="NEWS_UNAVAILABLE",
            items=[],
            reason=f"News provider {provider_name} returned {reason_code.lower()}.",
        )

    items: list[NewsItem] = []
    for raw in payload:
        if not isinstance(raw, Mapping):
            continue
        headline = _text(raw.get("headline"))
        url = _text(raw.get("url"))
        if not headline or not url:
            continue
        items.append(
            NewsItem(
                headline=headline,
                summary=_text(raw.get("summary")),
                url=url,
                image_url=_text(raw.get("image")) or None,
                source=_text(raw.get("source")) or provider_name,
                published_at=_published_at(raw.get("datetime")),
                related_symbol=related_symbol,
            )
        )
        if len(items) >= max(limit, 0):
            break

    if not items:
        return NewsResult(
            status="NEWS_UNAVAILABLE",
            items=[],
            reason=f"News provider {provider_name} returned no usable articles.",
        )
    return NewsResult(status="SUCCESS", items=items, reason=None)


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _published_at(value: Any) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    text = _text(value)
    return text or datetime.now(UTC).isoformat()


__all__ = ["NewsItem", "NewsResult", "normalize_news_result"]
