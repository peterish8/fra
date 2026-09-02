from __future__ import annotations

from copy import deepcopy
from typing import Any


class PublicationStore:
    def __init__(self) -> None:
        self._published: dict[str, dict[str, Any]] = {}
        self._staged: dict[str, dict[str, Any]] = {}

    def stage(self, period: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
        if period in self._staged:
            return deepcopy(self._staged[period])
        unique = {str(entry["company_id"]): dict(entry) for entry in entries}
        staged = {
            "period": period,
            "entries": sorted(unique.values(), key=lambda item: item.get("score", 0), reverse=True),
            "status": "STAGED",
        }
        self._staged[period] = staged
        return deepcopy(staged)

    def publish(self, period: str) -> dict[str, Any]:
        staged = self._staged.get(period)
        if staged is None or not staged["entries"]:
            raise ValueError("staged watchlist is empty")
        published = deepcopy(staged)
        published["status"] = "PUBLISHED"
        for index, entry in enumerate(published["entries"], 1):
            entry["rank"] = index
        self._published[period] = published
        return deepcopy(published)

    def latest(self) -> dict[str, Any] | None:
        return deepcopy(next(reversed(self._published.values()), None))

    def revert(self, period: str) -> dict[str, Any] | None:
        self._staged.pop(period, None)
        return self.latest()
