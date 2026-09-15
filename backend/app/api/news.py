"""Public company-news endpoint that powers the Daily News tab.

Headlines are not user-owned Truth Ledger content, so this endpoint is
intentionally unauthenticated, unlike the report/claim/source routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.providers.news.adapters import FinnhubNewsAdapter
from app.providers.news.contracts import NewsItem

router = APIRouter(prefix="/v1/news", tags=["news"])


class NewsResponse(BaseModel):
    status: str
    items: list[NewsItem]
    reason: str | None = None


@router.get("", response_model=NewsResponse)
async def get_company_news(
    request: Request,
    symbol: str = Query(..., min_length=1, max_length=12),
    limit: int = Query(default=5, ge=1, le=10),
) -> NewsResponse:
    """Return recent headlines for a symbol, or an explicit reason there are none."""

    adapter = getattr(request.app.state, "news_adapter", None)
    if adapter is None:
        settings = request.app.state.settings
        api_key = settings.finnhub_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            return NewsResponse(
                status="NOT_CONFIGURED",
                items=[],
                reason="Set FINNHUB_API_KEY to enable live company news.",
            )
        adapter = FinnhubNewsAdapter(api_key=api_key.get_secret_value())

    result = adapter.fetch_company_news(symbol, limit=limit)
    return NewsResponse(status=result.status, items=result.items, reason=result.reason)


def include_news_router(application: object) -> None:
    application.include_router(router)  # type: ignore[attr-defined]


__all__ = ["NewsResponse", "get_company_news", "include_news_router", "router"]
