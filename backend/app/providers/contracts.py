"""Stable, provider-neutral contracts for retrieval capabilities."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from math import isfinite
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProviderStatus(StrEnum):
    """Explicit outcomes exposed by every provider adapter."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    RATE_LIMITED = "RATE_LIMITED"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    PARSE_FAILED = "PARSE_FAILED"
    TIMEOUT = "TIMEOUT"
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"


class ProviderResult(BaseModel):
    """Typed, normalized and safe-to-audit provider output."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    status: ProviderStatus
    data: Any | None = None
    provider_request_id: str | None = None
    retrieved_at: str = Field(min_length=1)
    latency_ms: float = Field(ge=0)
    cost_usd_estimate: Decimal = Field(ge=0)
    safe_metadata: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    retry_classification: str = "NOT_RETRYABLE"


class SearchCapability(Protocol):
    """Capability implemented by an injectable search adapter."""

    provider: str
    estimated_cost_usd: Decimal

    def search(self, query: str, **kwargs: Any) -> ProviderResult:
        """Search public sources and return a normalized result."""


class ExtractionCapability(Protocol):
    """Capability implemented by an injectable public extractor."""

    provider: str
    estimated_cost_usd: Decimal

    def extract(self, url: str, **kwargs: Any) -> ProviderResult:
        """Extract permitted public content and return a normalized result."""


_SENSITIVE_KEY = re.compile(
    r"(?:^|[_-])(authorization|auth|cookie|set-cookie|api[-_]?key|access[-_]?token|"
    r"refresh[-_]?token|id[-_]?token|client[-_]?secret|password|passwd|secret|session|"
    r"credential|bearer|token)(?:$|[_-])",
    re.IGNORECASE,
)
_SENSITIVE_EXACT_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "id_token",
    "client_secret",
    "password",
    "passwd",
    "secret",
    "session",
    "credentials",
    "bearer",
    "token",
}
_RESTRICTED_MARKER = re.compile(
    r"(?:\b(?:please\s+)?(?:log\s*in|sign\s*in|login|signin)\b|"
    r"\b(?:authentication|authorization)\s+(?:required|needed)\b|"
    r"\b(?:paywall|premium\s+content|members?[- ]only)\b|"
    r"\bsubscribe\s+(?:to\s+)?(?:read|continue|access)\b|"
    r"\b(?:captcha|re\s*captcha|bot\s+check)\b|"
    r"\bverify\s+(?:that\s+)?you(?:'re|\s+are)\s+(?:a\s+)?human\b|"
    r"\baccess\s+denied\b)",
    re.IGNORECASE,
)


def _safe_metadata(value: Any, *, key: str | None = None) -> Any:
    """Recursively copy metadata and replace secret-bearing values."""

    if key is not None:
        normalized_key = key.strip().lower().replace(" ", "_")
        if normalized_key in _SENSITIVE_EXACT_KEYS or _SENSITIVE_KEY.search(normalized_key):
            return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): _safe_metadata(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe_metadata(item) for item in value]
    if isinstance(value, set):
        return [_safe_metadata(item) for item in sorted(value, key=repr)]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _contains_restricted_marker(value: Any) -> bool:
    if isinstance(value, str):
        return _RESTRICTED_MARKER.search(value) is not None
    if isinstance(value, Mapping):
        return any(_contains_restricted_marker(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_restricted_marker(item) for item in value)
    return False


def _timestamp(value: str | datetime) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
    return value


def _status(value: ProviderStatus | str | None) -> tuple[ProviderStatus, str | None]:
    candidate = value.value if isinstance(value, ProviderStatus) else str(value or "").upper()
    try:
        return ProviderStatus(candidate), None
    except ValueError:
        return ProviderStatus.PERMANENT_FAILURE, "INVALID_PROVIDER_STATUS"


def normalize_provider_result(
    *,
    provider: str,
    operation: str,
    payload: Any | None,
    provider_status: ProviderStatus | str | None,
    provider_request_id: str | None,
    retrieved_at: str | datetime,
    latency_ms: int | float | Decimal,
    cost_usd_estimate: Decimal | int | float | str | None,
    raw_metadata: Mapping[str, Any] | None,
    error_code: str | None,
    retry_classification: str,
) -> ProviderResult:
    """Normalize status, lineage, timing, cost and non-secret metadata."""

    status, status_error = _status(provider_status)
    metadata = _safe_metadata(raw_metadata or {})
    if not isinstance(metadata, dict):
        metadata = {"metadata": metadata}

    if status is ProviderStatus.SUCCESS and _contains_restricted_marker(payload):
        status = ProviderStatus.ACCESS_RESTRICTED
        payload = None
        error_code = error_code or ProviderStatus.ACCESS_RESTRICTED.value
    elif status is ProviderStatus.SUCCESS and payload is None:
        status = ProviderStatus.NO_RESULTS
        error_code = error_code or ProviderStatus.NO_RESULTS.value
    if status_error is not None:
        error_code = error_code or status_error

    try:
        cost = Decimal(str(cost_usd_estimate if cost_usd_estimate is not None else "0"))
    except (ArithmeticError, ValueError):
        cost = Decimal("0")
        error_code = error_code or "INVALID_COST"
    if not cost.is_finite() or cost < 0:
        cost = Decimal("0")
        error_code = error_code or "INVALID_COST"

    try:
        latency = float(latency_ms)
    except (TypeError, ValueError):
        latency = 0.0
        error_code = error_code or "INVALID_LATENCY"
    if not isfinite(latency) or latency < 0:
        latency = 0.0
        error_code = error_code or "INVALID_LATENCY"

    return ProviderResult(
        provider=provider.strip(),
        operation=operation.strip(),
        status=status,
        data=payload if status in {ProviderStatus.SUCCESS, ProviderStatus.PENDING} else None,
        provider_request_id=provider_request_id,
        retrieved_at=_timestamp(retrieved_at),
        latency_ms=latency,
        cost_usd_estimate=cost,
        safe_metadata=metadata,
        error_code=error_code,
        retry_classification=retry_classification,
    )


__all__ = [
    "ExtractionCapability",
    "ProviderResult",
    "ProviderStatus",
    "SearchCapability",
    "normalize_provider_result",
]
