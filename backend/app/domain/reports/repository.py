"""Persistence boundary for report workspaces.

The application uses this protocol so PostgreSQL/Supabase persistence can be
added without moving ownership or idempotency rules into HTTP handlers. The
fixture adapter deliberately only touches its supplied ``reports`` list and
never opens a network or database connection.
"""

from __future__ import annotations

import threading
from collections.abc import MutableSequence, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import UUID, uuid4

from .models import CreateReportRequest, ReportRecord, ReportStatus


class IdempotencyConflictError(ValueError):
    """The same user/action key was submitted with a different request."""


class ReportRepositoryUnavailable(RuntimeError):
    """No configured durable report repository is available."""


class ReportRepository(Protocol):
    """Repository contract required by :class:`ReportService`."""

    def create_report(
        self,
        *,
        owner_user_id: str,
        request: CreateReportRequest,
        idempotency_key: str | None,
        fingerprint: str,
    ) -> ReportRecord: ...

    def list_reports(
        self,
        *,
        owner_user_id: str,
        status: ReportStatus | None,
        company_id: UUID | None,
        query: str | None,
    ) -> Sequence[ReportRecord]: ...

    def get_report(self, report_id: UUID) -> ReportRecord | None: ...

    def soft_delete_report(self, report_id: UUID) -> ReportRecord | None: ...


class _CollectionReportRepository:
    """Shared behavior for local records and the frozen test repository."""

    def __init__(
        self,
        records: MutableSequence[dict[str, Any]],
        idempotency: dict[tuple[str, str], tuple[str, ReportRecord]] | None = None,
    ) -> None:
        self._records = records
        self._idempotency = idempotency if idempotency is not None else {}
        self._lock = threading.RLock()

    def create_report(
        self,
        *,
        owner_user_id: str,
        request: CreateReportRequest,
        idempotency_key: str | None,
        fingerprint: str,
    ) -> ReportRecord:
        with self._lock:
            if idempotency_key is not None:
                identity = (owner_user_id, idempotency_key)
                prior = self._idempotency.get(identity)
                if prior is not None:
                    prior_fingerprint, prior_record = prior
                    if prior_fingerprint != fingerprint:
                        raise IdempotencyConflictError
                    return prior_record

            now = datetime.now(UTC)
            record = ReportRecord(
                report_id=uuid4(),
                owner_user_id=owner_user_id,
                title=request.title,
                subject=request.subject,
                focus=request.focus,
                depth=request.depth,
                status=ReportStatus.DRAFT,
                updated_at=now,
            )
            self._records.append(_record_to_storage(record))
            if idempotency_key is not None:
                self._idempotency[(owner_user_id, idempotency_key)] = (fingerprint, record)
            return record

    def list_reports(
        self,
        *,
        owner_user_id: str,
        status: ReportStatus | None,
        company_id: UUID | None,
        query: str | None,
    ) -> Sequence[ReportRecord]:
        normalized_query = query.casefold() if query is not None else None
        records: list[ReportRecord] = []
        with self._lock:
            for raw in self._records:
                record = ReportRecord.from_storage(raw)
                if record.owner_user_id != owner_user_id or record.deleted_at is not None:
                    continue
                if status is not None and record.status != status:
                    continue
                if company_id is not None and record.company_id != company_id:
                    continue
                if normalized_query is not None and not _matches_query(record, normalized_query):
                    continue
                records.append(record)
        records.sort(key=lambda item: (item.updated_at, str(item.report_id)), reverse=True)
        return records

    def get_report(self, report_id: UUID) -> ReportRecord | None:
        with self._lock:
            for raw in self._records:
                record = ReportRecord.from_storage(raw)
                if record.report_id == report_id:
                    return record
        return None

    def soft_delete_report(self, report_id: UUID) -> ReportRecord | None:
        with self._lock:
            for raw in self._records:
                record = ReportRecord.from_storage(raw)
                if record.report_id != report_id or record.deleted_at is not None:
                    continue
                now = datetime.now(UTC)
                raw["deleted_at"] = now
                raw["updated_at"] = now
                return ReportRecord.from_storage(raw)
        return None


class InMemoryReportRepository(_CollectionReportRepository):
    """Small local repository useful for unit tests and development fixtures."""

    def __init__(self, records: Sequence[dict[str, Any]] | None = None) -> None:
        super().__init__(list(records or []))


class FixtureReportRepositoryAdapter(_CollectionReportRepository):
    """Adapt the frozen fixture's public ``reports`` collection to the contract."""

    def __init__(self, fixture_repository: object) -> None:
        records = getattr(fixture_repository, "reports", None)
        if not isinstance(records, list):
            raise ReportRepositoryUnavailable("fixture repository has no report collection")
        idempotency = getattr(fixture_repository, "_report_idempotency", None)
        if not isinstance(idempotency, dict):
            idempotency = {}
            vars(fixture_repository)["_report_idempotency"] = idempotency
        super().__init__(cast(MutableSequence[dict[str, Any]], records), idempotency)


def adapt_report_repository(repository: object) -> ReportRepository:
    """Return a repository implementation without making a live DB call."""

    required = ("create_report", "list_reports", "get_report", "soft_delete_report")
    if all(callable(getattr(repository, name, None)) for name in required):
        return cast(ReportRepository, repository)
    if isinstance(getattr(repository, "reports", None), list):
        return FixtureReportRepositoryAdapter(repository)
    raise ReportRepositoryUnavailable("report repository is not configured")


def _record_to_storage(record: ReportRecord) -> dict[str, Any]:
    return {
        "report_id": str(record.report_id),
        "owner_user_id": record.owner_user_id,
        "title": record.title,
        "subject": record.subject.model_dump(exclude_none=True),
        "focus": list(record.focus),
        "depth": record.depth.value,
        "status": record.status.value,
        "updated_at": record.updated_at,
        "deleted_at": record.deleted_at,
        "current_version": record.current_version,
        "company_id": str(record.company_id) if record.company_id is not None else None,
    }


def _matches_query(record: ReportRecord, query: str) -> bool:
    searchable = (
        record.title,
        record.subject.query,
        record.subject.ticker or "",
        record.subject.domain or "",
    )
    return any(query in value.casefold() for value in searchable)


__all__ = [
    "FixtureReportRepositoryAdapter",
    "IdempotencyConflictError",
    "InMemoryReportRepository",
    "ReportRepository",
    "ReportRepositoryUnavailable",
    "adapt_report_repository",
]
