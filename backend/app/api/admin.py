"""Administrative observability endpoints."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Request

from app.domain.admin_usage import AdminUsageOverview, AdminUsageRepository
from app.security.auth import AuthenticatedUser, require_admin
from app.security.errors import stable_http_error

router = APIRouter(prefix="/v1/admin", tags=["admin"])
_admin_dependency = Depends(require_admin)


@router.get("/usage-overview", response_model=AdminUsageOverview)
async def get_usage_overview(
    request: Request,
    _: AuthenticatedUser = _admin_dependency,
) -> AdminUsageOverview:
    """Return quota and activity summaries without exposing private credentials."""

    repository = getattr(request.app.state, "admin_usage_repository", None)
    get_overview = getattr(repository, "get_overview", None)
    if not callable(get_overview):
        request_id = getattr(request.state, "request_id", "req_unavailable")
        raise stable_http_error(
            status_code=503,
            code="ADMIN_USAGE_UNAVAILABLE",
            message="Administrative usage data is not configured for this environment.",
            request_id=request_id if isinstance(request_id, str) else "req_unavailable",
        )
    return cast(AdminUsageRepository, repository).get_overview()


__all__ = ["get_usage_overview", "router"]
