"""Owner-authorized, report-scoped source lineage HTTP boundary."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Protocol, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from app.api.dependencies import assert_owner
from app.domain.reports import (
    ReportRepository,
    ReportRepositoryUnavailable,
    adapt_report_repository,
)
from app.security.auth import AuthenticatedUser, get_current_user
from app.security.errors import stable_http_error

router = APIRouter(prefix="/v1/reports", tags=["sources"])
_current_user_dependency = Depends(get_current_user)


class SourceSnapshotSummary(BaseModel):
    """Retention-safe source snapshot summary; full content is never returned here."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: UUID
    retrieved_at: datetime
    published_at: datetime | None = None
    content_hash: str
    retention_mode: str
    provider_request_id: UUID | None = None


class ReportSourceSummary(BaseModel):
    """Source lineage visible only through an authorized report relationship."""

    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    identity_key: str
    canonical_url: str | None = None
    publisher: str
    domain: str | None = None
    source_type: str
    authority_tier: str
    ownership_relation: str
    source_family_id: UUID | None = None
    source_family_reason: str | None = None
    latest_snapshot: SourceSnapshotSummary


class ReportSourcePage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ReportSourceSummary]
    next_cursor: str | None = None


class ReportSourceRepository(Protocol):
    """Persistence projection constrained to sources reachable from one report."""

    def list_report_sources(
        self, *, report_id: UUID, cursor: str | None, limit: int
    ) -> ReportSourcePage: ...


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) and value else "req_unavailable"


def _report_repository(request: Request) -> ReportRepository:
    repository = getattr(request.app.state, "report_repository", None)
    try:
        return adapt_report_repository(repository)
    except ReportRepositoryUnavailable as error:
        raise stable_http_error(
            status_code=503,
            code="REPORT_STORE_UNAVAILABLE",
            message="Report workspace storage is not configured.",
            request_id=_request_id(request),
        ) from error


def _source_repository(request: Request) -> ReportSourceRepository:
    repository = getattr(request.app.state, "report_source_repository", None)
    if not callable(getattr(repository, "list_report_sources", None)):
        raise stable_http_error(
            status_code=503,
            code="SOURCE_STORE_UNAVAILABLE",
            message="Source lineage storage is not configured.",
            request_id=_request_id(request),
        )
    return cast(ReportSourceRepository, repository)


@router.get("/{report_id}/sources", response_model=ReportSourcePage)
async def list_report_sources(
    report_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
) -> ReportSourcePage:
    """List retention-safe source provenance after report-owner authorization."""

    report = _report_repository(request).get_report(report_id)
    if report is None or report.deleted_at is not None:
        raise stable_http_error(
            status_code=404,
            code="NOT_FOUND",
            message="The requested report was not found.",
            request_id=_request_id(request),
        )
    assert_owner(
        current_user_id=current_user.id,
        resource_owner_id=report.owner_user_id,
        request_id=_request_id(request),
    )
    return _source_repository(request).list_report_sources(
        report_id=report_id,
        cursor=cursor,
        limit=limit,
    )


def include_source_router(application: object) -> None:
    include_router = getattr(application, "include_router", None)
    if not callable(include_router):
        raise TypeError("application must provide include_router")
    include_router(router)


__all__ = [
    "ReportSourcePage",
    "ReportSourceRepository",
    "ReportSourceSummary",
    "SourceSnapshotSummary",
    "include_source_router",
    "list_report_sources",
    "router",
]
