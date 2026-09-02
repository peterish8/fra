"""Run/provider cost accounting with explicit budget decisions."""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class CostEntry:
    provider: str
    operation: str
    cost_usd: float
    run_id: str | None = None


class CostLedger:
    """In-process accounting projection; durable run cost remains persisted by workers."""

    def __init__(self, *, budget_usd: float | None = None) -> None:
        if budget_usd is not None and (not math.isfinite(budget_usd) or budget_usd < 0):
            raise ValueError("budget_usd must be finite and non-negative")
        self.budget_usd = budget_usd
        self._entries: list[CostEntry] = []
        self._lock = threading.RLock()

    def record(
        self,
        *,
        provider: str,
        operation: str,
        cost_usd: float,
        run_id: str | None = None,
    ) -> CostEntry:
        if not provider.strip() or not operation.strip():
            raise ValueError("provider and operation are required")
        if not math.isfinite(cost_usd) or cost_usd < 0:
            raise ValueError("cost_usd must be finite and non-negative")
        entry = CostEntry(provider=provider, operation=operation, cost_usd=cost_usd, run_id=run_id)
        with self._lock:
            self._entries.append(entry)
        return entry

    @property
    def total_usd(self) -> float:
        with self._lock:
            return round(sum(entry.cost_usd for entry in self._entries), 8)

    def within_budget(self, *, additional_usd: float = 0.0) -> bool:
        if additional_usd < 0 or not math.isfinite(additional_usd):
            raise ValueError("additional_usd must be finite and non-negative")
        return self.budget_usd is None or self.total_usd + additional_usd <= self.budget_usd

    def summary(self) -> dict[str, object]:
        with self._lock:
            by_provider: dict[str, float] = {}
            by_operation: dict[str, float] = {}
            for entry in self._entries:
                by_provider[entry.provider] = by_provider.get(entry.provider, 0.0) + entry.cost_usd
                by_operation[entry.operation] = (
                    by_operation.get(entry.operation, 0.0) + entry.cost_usd
                )
            total = round(sum(by_provider.values()), 8)
            return {
                "total_usd": total,
                "budget_usd": self.budget_usd,
                "remaining_usd": (
                    round(self.budget_usd - total, 8) if self.budget_usd is not None else None
                ),
                "by_provider": {key: round(value, 8) for key, value in by_provider.items()},
                "by_operation": {key: round(value, 8) for key, value in by_operation.items()},
                "calls": len(self._entries),
            }


__all__ = ["CostEntry", "CostLedger"]
