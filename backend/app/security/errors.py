"""Stable API errors used at authentication and authorization boundaries."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def stable_error_detail(
    *,
    code: str,
    message: str,
    request_id: str,
    details: Any = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
    }
    if details is not None:
        error["details"] = details
    return {"error": error}


def stable_http_error(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: Any = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=stable_error_detail(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        ),
    )


__all__ = ["stable_error_detail", "stable_http_error"]
