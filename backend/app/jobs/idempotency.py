"""Durable-idempotency boundary used by long-running jobs.

The in-memory implementation is intentionally small and deterministic for
local workers.  ``IdempotencyStore`` is the contract a PostgreSQL adapter
implements with a unique ``idempotency_key`` constraint and a transaction.
No caller is allowed to create a second resource for an already-recorded
fingerprint.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


class IdempotencyConflictError(ValueError):
    """An idempotency key was replayed with a different request."""


@dataclass(frozen=True)
class IdempotencyRecord[T]:
    """The original resource and request fingerprint for one replay key."""

    scope: str
    key: str
    fingerprint: str
    resource: T


@dataclass(frozen=True)
class IdempotencyResult[T]:
    """Result of an idempotent create-or-replay operation."""

    resource: T
    created: bool


class IdempotencyStore[T]:
    """Thread-safe local implementation of the durable idempotency contract.

    Production persistence should provide the same atomic semantics using a
    unique scope/key index.  The store never calls the factory while another
    request can observe a partially-created record.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], IdempotencyRecord[T]] = {}
        self._lock = threading.RLock()

    def get(self, *, scope: str, key: str) -> IdempotencyRecord[T] | None:
        _validate_identity(scope, key)
        with self._lock:
            return self._records.get((scope, key))

    def get_or_create(
        self,
        *,
        scope: str,
        key: str,
        fingerprint: str,
        factory: Callable[[], T],
    ) -> IdempotencyResult[T]:
        _validate_identity(scope, key)
        if not fingerprint.strip():
            raise ValueError("idempotency fingerprint must not be blank")
        with self._lock:
            identity = (scope, key)
            prior = self._records.get(identity)
            if prior is not None:
                if prior.fingerprint != fingerprint:
                    raise IdempotencyConflictError(
                        "idempotency key was already used with a different request"
                    )
                return IdempotencyResult(resource=prior.resource, created=False)

            resource = factory()
            self._records[identity] = IdempotencyRecord(
                scope=scope,
                key=key,
                fingerprint=fingerprint,
                resource=resource,
            )
            return IdempotencyResult(resource=resource, created=True)

    def put(
        self,
        *,
        scope: str,
        key: str,
        fingerprint: str,
        resource: T,
    ) -> IdempotencyRecord[T]:
        """Insert a known resource, accepting an exact replay only."""

        _validate_identity(scope, key)
        if not fingerprint.strip():
            raise ValueError("idempotency fingerprint must not be blank")
        with self._lock:
            identity = (scope, key)
            prior = self._records.get(identity)
            if prior is not None:
                if prior.fingerprint != fingerprint or prior.resource != resource:
                    raise IdempotencyConflictError(
                        "idempotency key was already used with a different resource"
                    )
                return prior
            record = IdempotencyRecord(
                scope=scope,
                key=key,
                fingerprint=fingerprint,
                resource=resource,
            )
            self._records[identity] = record
            return record

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)


class IdempotencyService(IdempotencyStore[T]):
    """Compatibility name for application code that calls this a service."""


def _validate_identity(scope: str, key: str) -> None:
    if not isinstance(scope, str) or not scope.strip():
        raise ValueError("idempotency scope must not be blank")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("idempotency key must not be blank")


__all__ = [
    "IdempotencyConflictError",
    "IdempotencyRecord",
    "IdempotencyResult",
    "IdempotencyService",
    "IdempotencyStore",
]
