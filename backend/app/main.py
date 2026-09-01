"""FastAPI application factory for the Financial Research Agent API."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.companies import include_company_router
from app.api.reports import include_report_router
from app.api.routes.health import router as health_router
from app.api.routes.health import versioned_router as versioned_health_router
from app.api.routes.me import router as me_router
from app.config.settings import Settings, get_settings
from app.observability.middleware import RequestLoggingMiddleware
from app.security.auth import AuthenticatedUser, TokenVerifier, verify_access_token


def _http_exception_response(_: Request, exception: Exception) -> JSONResponse:
    """Return the documented error envelope instead of FastAPI's ``detail`` wrapper."""

    if not isinstance(exception, HTTPException):
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": "The request could not be completed.",
                    "request_id": "req_unavailable",
                }
            },
        )

    detail: Any = exception.detail
    if isinstance(detail, dict) and "error" in detail:
        payload = detail
    else:
        payload = {
            "error": {
                "code": "HTTP_ERROR",
                "message": str(detail),
                "request_id": "req_unavailable",
            }
        }
    return JSONResponse(status_code=exception.status_code, content=payload)


def create_app(
    *,
    settings: Settings | None = None,
    token_verifier: TokenVerifier | Callable[..., AuthenticatedUser] | None = None,
) -> FastAPI:
    """Create an independently testable API application."""

    resolved_settings = settings if settings is not None else get_settings()
    application = FastAPI(
        title="Financial Research Agent API",
        version="0.1.0",
        docs_url="/docs" if resolved_settings.app_env != "production" else None,
        redoc_url="/redoc" if resolved_settings.app_env != "production" else None,
    )
    application.state.settings = resolved_settings
    application.state.token_verifier = token_verifier or verify_access_token

    application.add_middleware(RequestLoggingMiddleware)
    application.add_exception_handler(HTTPException, _http_exception_response)

    async def validation_exception_response(
        request: Request,
        exception: Exception,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "req_unavailable")
        details = exception.errors() if isinstance(exception, RequestValidationError) else None
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request could not be validated.",
                    "request_id": request_id,
                    "details": details,
                }
            },
        )

    application.add_exception_handler(RequestValidationError, validation_exception_response)
    application.include_router(health_router)
    application.include_router(versioned_health_router)
    application.include_router(me_router)
    include_company_router(application)
    include_report_router(application)
    return application


__all__ = ["create_app"]
