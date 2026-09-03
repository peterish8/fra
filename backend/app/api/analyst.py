"""Owner-scoped analyst workflow endpoints.

These endpoints expose research posture and cited projections. They never
create unbacked factual claims or treat a thesis status as a verification
verdict.
"""

from __future__ import annotations

from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import assert_owner
from app.domain.analyst import (
    AnalystWorkflowRepository,
    ChangeBrief,
    ChangeBriefKind,
    Tearsheet,
    ThesisPoint,
    ThesisPointCreate,
    ThesisPointUpdate,
)
from app.domain.analyst.projections import build_change_brief, build_tearsheet
from app.domain.reports import ReportRecord, ReportRepositoryUnavailable, ReportService
from app.security.auth import AuthenticatedUser, get_current_user
from app.security.errors import stable_http_error

router = APIRouter(prefix="/v1/reports", tags=["analyst-workflow"])
_current_user_dependency = Depends(get_current_user)


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) and request_id else "req_unavailable"


def _not_found(request: Request) -> NoReturn:
    raise stable_http_error(
        status_code=404,
        code="NOT_FOUND",
        message="The requested report or analyst item was not found.",
        request_id=_request_id(request),
    )


def _report(request: Request, report_id: UUID, current_user: AuthenticatedUser) -> ReportRecord:
    repository = getattr(request.app.state, "report_repository", None)
    if repository is None:
        raise stable_http_error(
            status_code=503,
            code="REPORT_STORE_UNAVAILABLE",
            message="Report workspace storage is not configured.",
            request_id=_request_id(request),
        )
    try:
        report = ReportService(repository).get(report_id)
    except ReportRepositoryUnavailable as error:
        raise stable_http_error(
            status_code=503,
            code="REPORT_STORE_UNAVAILABLE",
            message="Report workspace storage is not configured.",
            request_id=_request_id(request),
        ) from error
    if report is None or report.deleted_at is not None:
        _not_found(request)
    assert_owner(
        current_user_id=current_user.id,
        resource_owner_id=report.owner_user_id,
        request_id=_request_id(request),
    )
    return report


def _workflow_repository(request: Request) -> AnalystWorkflowRepository:
    repository = getattr(request.app.state, "analyst_workflow_repository", None)
    if not isinstance(repository, AnalystWorkflowRepository):
        raise stable_http_error(
            status_code=503,
            code="ANALYST_WORKFLOW_UNAVAILABLE",
            message="Analyst workflow storage is not configured.",
            request_id=_request_id(request),
        )
    return repository


@router.get("/{report_id}/thesis", response_model=list[ThesisPoint])
async def list_thesis_points(
    report_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
) -> list[ThesisPoint]:
    _report(request, report_id, current_user)
    return _workflow_repository(request).list_thesis_points(report_id)


@router.post("/{report_id}/thesis", response_model=ThesisPoint, status_code=201)
async def create_thesis_point(
    report_id: UUID,
    payload: ThesisPointCreate,
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
) -> ThesisPoint:
    _report(request, report_id, current_user)
    return _workflow_repository(request).create_thesis_point(report_id, payload)


@router.patch("/{report_id}/thesis/{thesis_point_id}", response_model=ThesisPoint)
async def update_thesis_point(
    report_id: UUID,
    thesis_point_id: UUID,
    payload: ThesisPointUpdate,
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
) -> ThesisPoint:
    _report(request, report_id, current_user)
    updated = _workflow_repository(request).update_thesis_point(report_id, thesis_point_id, payload)
    if updated is None:
        _not_found(request)
    return updated


@router.get("/{report_id}/change-brief", response_model=ChangeBrief)
async def get_change_brief(
    report_id: UUID,
    request: Request,
    kind: ChangeBriefKind = ChangeBriefKind.EARNINGS,
    current_user: AuthenticatedUser = _current_user_dependency,
) -> ChangeBrief:
    report = _report(request, report_id, current_user)
    return build_change_brief(report, kind)


@router.get("/{report_id}/tearsheet", response_model=Tearsheet)
async def get_tearsheet(
    report_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
) -> Tearsheet:
    report = _report(request, report_id, current_user)
    thesis_points = _workflow_repository(request).list_thesis_points(report_id)
    return build_tearsheet(report, thesis_points)


def include_analyst_router(application: object) -> None:
    include_router = getattr(application, "include_router", None)
    if not callable(include_router):
        raise TypeError("application must provide include_router")
    include_router(router)


__all__ = ["include_analyst_router", "router"]
