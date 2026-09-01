"""Protected HTTP endpoints for report workspaces."""

from __future__ import annotations

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from app.api.dependencies import assert_owner
from app.domain.reports import (
    CreateReportRequest,
    IdempotencyConflictError,
    InvalidReportCursor,
    ReportDetail,
    ReportListResponse,
    ReportRepositoryUnavailable,
    ReportService,
    ReportStatus,
    ReportSummary,
)
from app.security.auth import AuthenticatedUser, get_current_user
from app.security.errors import stable_http_error

router = APIRouter(prefix="/v1/reports", tags=["reports"])
_current_user_dependency = Depends(get_current_user)
_idempotency_header = Annotated[
    str | None, Header(alias="Idempotency-Key", min_length=8, max_length=128)
]


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) and request_id else "req_unavailable"


def _service(request: Request) -> ReportService:
    repository = getattr(request.app.state, "report_repository", None)
    if repository is None:
        raise stable_http_error(
            status_code=503,
            code="REPORT_STORE_UNAVAILABLE",
            message="Report workspace storage is not configured.",
            request_id=_request_id(request),
        )
    try:
        return ReportService(repository)
    except ReportRepositoryUnavailable as error:
        raise stable_http_error(
            status_code=503,
            code="REPORT_STORE_UNAVAILABLE",
            message="Report workspace storage is not configured.",
            request_id=_request_id(request),
        ) from error


def _not_found(request: Request) -> NoReturn:
    raise stable_http_error(
        status_code=404,
        code="NOT_FOUND",
        message="The requested report was not found.",
        request_id=_request_id(request),
    )


@router.post("", response_model=ReportSummary, status_code=201)
async def create_report(
    payload: CreateReportRequest,
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
    idempotency_key: _idempotency_header = None,
) -> ReportSummary:
    try:
        return _service(request).create(
            owner_user_id=current_user.id,
            request=payload,
            idempotency_key=idempotency_key,
        )
    except IdempotencyConflictError as error:
        raise stable_http_error(
            status_code=409,
            code="IDEMPOTENCY_CONFLICT",
            message="The idempotency key was already used with a different request.",
            request_id=_request_id(request),
        ) from error


@router.get("", response_model=ReportListResponse)
async def list_reports(
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
    q: str | None = None,
    status: ReportStatus | None = None,
    company_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
) -> ReportListResponse:
    try:
        return _service(request).list(
            owner_user_id=current_user.id,
            limit=limit,
            cursor=cursor,
            query=q,
            status=status,
            company_id=company_id,
        )
    except InvalidReportCursor as error:
        raise stable_http_error(
            status_code=422,
            code="VALIDATION_ERROR",
            message="The request could not be validated.",
            request_id=_request_id(request),
        ) from error


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
) -> ReportDetail:
    service = _service(request)
    report = service.get(report_id)
    if report is None or report.deleted_at is not None:
        _not_found(request)
    assert_owner(
        current_user_id=current_user.id,
        resource_owner_id=report.owner_user_id,
        request_id=_request_id(request),
    )
    return service.detail(report)


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
) -> Response:
    service = _service(request)
    report = service.get(report_id)
    if report is None or report.deleted_at is not None:
        _not_found(request)
    assert_owner(
        current_user_id=current_user.id,
        resource_owner_id=report.owner_user_id,
        request_id=_request_id(request),
    )
    service.soft_delete(report_id)
    return Response(status_code=204)


def include_report_router(application: object) -> None:
    """Install the router from an application factory without coupling the domain."""

    include_router = getattr(application, "include_router", None)
    if not callable(include_router):
        raise TypeError("application must provide include_router")
    include_router(router)


__all__ = [
    "create_report",
    "delete_report",
    "get_report",
    "include_report_router",
    "list_reports",
    "router",
]
