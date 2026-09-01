"""Report workspace business rules and cursor pagination."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from .models import (
    CreateReportRequest,
    ReportDetail,
    ReportListResponse,
    ReportRecord,
    ReportStatus,
    ReportSummary,
)
from .repository import ReportRepository, adapt_report_repository


class InvalidReportCursor(ValueError):
    """The opaque list cursor is malformed or does not match its format."""


class ReportService:
    """Application-facing report operations independent of FastAPI."""

    def __init__(self, repository: object) -> None:
        self._repository: ReportRepository = adapt_report_repository(repository)

    def create(
        self,
        *,
        owner_user_id: str,
        request: CreateReportRequest,
        idempotency_key: str | None,
    ) -> ReportSummary:
        fingerprint = _request_fingerprint(request)
        record = self._repository.create_report(
            owner_user_id=owner_user_id,
            request=request,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
        return ReportSummary.from_record(record)

    def list(
        self,
        *,
        owner_user_id: str,
        limit: int,
        cursor: str | None,
        query: str | None,
        status: ReportStatus | None,
        company_id: UUID | None,
    ) -> ReportListResponse:
        records = list(
            self._repository.list_reports(
                owner_user_id=owner_user_id,
                status=status,
                company_id=company_id,
                query=query.strip() if query is not None else None,
            )
        )
        start = _cursor_offset(records, cursor)
        page = records[start : start + limit]
        next_cursor = None
        if start + limit < len(records):
            next_cursor = _encode_cursor(page[-1])
        return ReportListResponse(
            items=[ReportSummary.from_record(record) for record in page],
            next_cursor=next_cursor,
        )

    def get(self, report_id: UUID) -> ReportRecord | None:
        return self._repository.get_report(report_id)

    def detail(self, report: ReportRecord) -> ReportDetail:
        return ReportDetail.from_record(report)

    def soft_delete(self, report_id: UUID) -> ReportRecord | None:
        return self._repository.soft_delete_report(report_id)


def _request_fingerprint(request: CreateReportRequest) -> str:
    payload = request.model_dump(mode="json", exclude_none=True)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _encode_cursor(record: ReportRecord) -> str:
    payload = {"updated_at": record.updated_at.isoformat(), "report_id": str(record.report_id)}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
        updated_at = datetime.fromisoformat(str(payload["updated_at"]))
        report_id = UUID(str(payload["report_id"]))
    except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as error:
        raise InvalidReportCursor from error
    return updated_at, report_id


def _cursor_offset(records: Sequence[ReportRecord], cursor: str | None) -> int:
    if cursor is None:
        return 0
    updated_at, report_id = _decode_cursor(cursor)
    for index, record in enumerate(records):
        if record.updated_at == updated_at and record.report_id == report_id:
            return index + 1
    return 0


__all__ = ["InvalidReportCursor", "ReportService"]
