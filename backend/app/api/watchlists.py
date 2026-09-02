from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/v1/watchlists", tags=["watchlists"])


class WatchlistResponse(BaseModel):
    period: str | None = None
    status: str = "EMPTY"
    methodology_version: str = "watchlist-v1"
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []


@router.get("/latest", response_model=WatchlistResponse)
async def latest_watchlist(request: Request) -> WatchlistResponse:
    store = getattr(request.app.state, "watchlist_store", None)
    latest = (
        store.latest() if store is not None and callable(getattr(store, "latest", None)) else None
    )
    if not latest:
        return WatchlistResponse(warnings=["NO_PUBLISHED_WATCHLIST"])
    return WatchlistResponse(
        period=latest.get("period"),
        status=latest.get("status", "PUBLISHED"),
        entries=latest.get("entries", []),
    )


__all__ = ["WatchlistResponse", "latest_watchlist", "router"]
