from __future__ import annotations

from datetime import date
from typing import Any

from app.jobs.idempotency import IdempotencyStore

WATCHLIST_WEEKLY = "WATCHLIST_WEEKLY"


def enqueue_weekly_watchlist(
    period: str | date, store: IdempotencyStore[Any]
) -> dict[str, str | bool]:
    key = f"{WATCHLIST_WEEKLY}:{period}"
    result = store.get_or_create(
        scope=WATCHLIST_WEEKLY,
        key=str(period),
        fingerprint=key,
        factory=lambda: key,
    )
    return {"idempotency_key": key, "enqueued": result.created}
