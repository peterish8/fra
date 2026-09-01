"""Reusable API dependencies and object-ownership checks."""

from __future__ import annotations

from fastapi import HTTPException

from app.security.errors import stable_http_error


def assert_owner(
    *,
    current_user_id: str | None,
    resource_owner_id: str,
    request_id: str,
) -> None:
    """Raise a stable authentication/authorization error when ownership fails."""

    if current_user_id is None or not current_user_id.strip():
        raise stable_http_error(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Authentication is required to access this resource.",
            request_id=request_id,
        )
    if current_user_id != resource_owner_id:
        raise stable_http_error(
            status_code=403,
            code="FORBIDDEN",
            message="You do not have permission to access this resource.",
            request_id=request_id,
        )


__all__ = ["assert_owner", "HTTPException"]
