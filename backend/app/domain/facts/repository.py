"""Replaceable persistence boundary for typed facts."""

from __future__ import annotations

from collections.abc import Sequence
from threading import RLock
from typing import Protocol
from uuid import UUID

from .models import FactRecord


class FactRepository(Protocol):
    def save(self, fact: FactRecord) -> FactRecord: ...

    def get(self, fact_id: UUID) -> FactRecord | None: ...

    def list_for_snapshot(self, source_snapshot_id: UUID) -> Sequence[FactRecord]: ...


class InMemoryFactRepository:
    """Deterministic local repository for tests and development."""

    def __init__(self) -> None:
        self.facts: dict[UUID, FactRecord] = {}
        self._lock = RLock()

    def save(self, fact: FactRecord) -> FactRecord:
        with self._lock:
            self.facts[fact.fact_id] = fact
        return fact

    def get(self, fact_id: UUID) -> FactRecord | None:
        return self.facts.get(fact_id)

    def list_for_snapshot(self, source_snapshot_id: UUID) -> Sequence[FactRecord]:
        return [
            fact for fact in self.facts.values() if fact.source_snapshot_id == source_snapshot_id
        ]


__all__ = ["FactRepository", "InMemoryFactRepository"]
