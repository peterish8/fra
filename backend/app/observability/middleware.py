"""Secret-safe structured request logging and correlation IDs."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Mapping
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

LOGGER = logging.getLogger("financial_research_agent.http")
REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SENSITIVE_HEADER_NAMES = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "proxy-authorization",
        "x-api-key",
        "x-auth-token",
        "x-csrf-token",
    }
)


def new_request_id() -> str:
    """Create a short, log-safe correlation ID."""

    return f"req_{uuid.uuid4().hex}"


def normalize_request_id(candidate: str | None) -> str:
    """Accept only bounded header values that are safe to log and echo."""

    if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return new_request_id()


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return headers safe for diagnostics, redacting sensitive values."""

    return {
        name: "[REDACTED]" if name.lower() in SENSITIVE_HEADER_NAMES else value
        for name, value in headers.items()
    }


def _json_log(event: Mapping[str, Any]) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), default=str)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Install request IDs and emit one secret-free JSON event per request."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started = time.perf_counter()
        response: Response | None = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            LOGGER.info(
                _json_log(
                    {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "level": "INFO",
                        "service": "financial-research-agent-api",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": duration_ms,
                    }
                )
            )


__all__ = [
    "LOGGER",
    "REQUEST_ID_HEADER",
    "RequestLoggingMiddleware",
    "SENSITIVE_HEADER_NAMES",
    "new_request_id",
    "normalize_request_id",
    "redact_headers",
]
