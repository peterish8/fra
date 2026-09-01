"""Application package and testable FastAPI application factory.

The public factory lives here so the foundation can be used before the
deployment entry point is introduced.  A small ``app.main`` compatibility
module is registered for the frozen foundation tests and for conventional
ASGI imports; it does not create an application or load settings at import
time.
"""

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.health import versioned_router as versioned_health_router
from app.api.routes.me import router as me_router
from app.config.settings import Settings, get_settings
from app.observability.middleware import RequestLoggingMiddleware
from app.security.auth import AuthenticatedUser, TokenVerifier, verify_access_token


def _request_id(request: Request) -> str:
    """Return the request ID installed by the middleware, if available."""

    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return "req_unavailable"


def _error_body(
    request: Request,
    *,
    code: str,
    message: str,
    details: Any = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": _request_id(request),
    }
    if details is not None:
        error["details"] = details
    return {"error": error}


def create_app(
    *,
    settings: Settings | None = None,
    token_verifier: TokenVerifier | Callable[..., AuthenticatedUser] | None = None,
) -> FastAPI:
    """Build the API application with injectable, deterministic boundaries.

    ``token_verifier`` is deliberately injectable for fixture tests and local
    development.  Production callers use the default server-side JWT
    verifier, which never calls Supabase over the network.
    """

    resolved_settings = settings or get_settings()
    application = FastAPI(
        title="Financial Research Agent API",
        version="0.1.0",
        docs_url=None if resolved_settings.app_env == "production" else "/docs",
        redoc_url=None if resolved_settings.app_env == "production" else "/redoc",
    )
    application.state.settings = resolved_settings
    application.state.token_verifier = token_verifier or verify_access_token
    application.add_middleware(RequestLoggingMiddleware)

    application.include_router(health_router)
    application.include_router(versioned_health_router)
    application.include_router(me_router)

    @application.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exception: HTTPException,
    ) -> JSONResponse:
        if isinstance(exception.detail, dict) and "error" in exception.detail:
            content = exception.detail
        else:
            code_by_status = {
                401: "UNAUTHENTICATED",
                403: "FORBIDDEN",
                404: "NOT_FOUND",
            }
            content = _error_body(
                request,
                code=code_by_status.get(exception.status_code, "HTTP_ERROR"),
                message=str(exception.detail),
            )
        return JSONResponse(
            status_code=exception.status_code,
            content=content,
            headers=exception.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                request,
                code="VALIDATION_ERROR",
                message="The request could not be validated.",
                details=exception.errors(),
            ),
        )

    return application


# ``backend/app/main.py`` is reserved by the repository work split.  Expose
# the conventional import without adding or modifying that protected file.
_main_module = types.ModuleType("app.main")
_main_module.create_app = create_app
_main_module.__doc__ = "Compatibility entry point for the FastAPI application factory."
sys.modules.setdefault("app.main", _main_module)


__all__ = ["create_app"]
