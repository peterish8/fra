"""Secret-safe diagnostics for operator-facing run and provider events.

Diagnostics are deliberately projections, not a second source of truth.  They
contain identifiers, states, timings and bounded error text so an operator can
explain a run without exposing prompts, source content or credentials.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

_REDACT_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "client_secret",
        "cookie",
        "database_url",
        "dsn",
        "password",
        "private_key",
        "prompt",
        "secret",
        "service_role_key",
        "supabase_service_role_key",
        "token",
    }
)
_SECRET_TEXT_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|authorization|cookie|password|secret|token)\s*[:=]\s*"
        r"(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
    ),
    re.compile(r"(?i)(https?://)[^/@\s]+@"),
)


def _is_secret_key(key: object) -> bool:
    normalized = str(key).strip().lower().replace("-", "_")
    return normalized in _REDACT_KEYS or any(
        fragment in normalized
        for fragment in ("api_key", "authorization", "cookie", "password", "secret", "token")
    )


def _redact_text(value: str, *, max_length: int) -> str:
    scrubbed = value
    for pattern in _SECRET_TEXT_PATTERNS:
        scrubbed = pattern.sub("[REDACTED]", scrubbed)
    return scrubbed[:max_length]


def safe_diagnostics(
    event: Mapping[str, Any],
    *,
    max_depth: int = 10,
    max_string_length: int = 2_000,
) -> dict[str, Any]:
    """Recursively redact credentials and prompts from a diagnostic payload.

    The function accepts arbitrary provider/error payloads but emits only plain
    JSON-compatible values.  Depth and string limits prevent diagnostics from
    becoming an accidental source-content dump.
    """

    if max_depth < 1 or max_string_length < 1:
        raise ValueError("diagnostic limits must be positive")

    def scrub(value: Any, depth: int) -> Any:
        if depth > max_depth:
            return "[TRUNCATED]"
        if isinstance(value, Mapping):
            return {
                str(key): "[REDACTED]" if _is_secret_key(key) else scrub(item, depth + 1)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set, frozenset)):
            return [scrub(item, depth + 1) for item in value]
        if isinstance(value, str):
            return _redact_text(value, max_length=max_string_length)
        if isinstance(value, (int, str, bool)) or value is None:
            return value
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        return _redact_text(str(value), max_length=max_string_length)

    result = scrub(dict(event), 0)
    return result if isinstance(result, dict) else {}


def lineage_event(
    *,
    run_id: str,
    stage: str,
    status: str,
    provider: str | None = None,
    cost_usd: float = 0.0,
    duration_ms: float | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Build one safe, structured event for a run/provider lineage stream."""

    if not run_id.strip() or not stage.strip() or not status.strip():
        raise ValueError("run_id, stage, and status are required")
    if not math.isfinite(cost_usd) or cost_usd < 0:
        raise ValueError("cost_usd must be finite and non-negative")
    if duration_ms is not None and (not math.isfinite(duration_ms) or duration_ms < 0):
        raise ValueError("duration_ms must be finite and non-negative")
    payload: dict[str, Any] = {
        "run_id": run_id,
        "stage": stage,
        "status": status,
        "provider": provider,
        "cost_usd": round(cost_usd, 8),
        **({"duration_ms": round(duration_ms, 2)} if duration_ms is not None else {}),
        **fields,
    }
    return safe_diagnostics(payload)


def safe_run_debug(
    *,
    run_id: str,
    status: str,
    stages: Sequence[Mapping[str, Any]] = (),
    provider_calls: Sequence[Mapping[str, Any]] = (),
    blockers: Sequence[str] = (),
    cost_usd: float = 0.0,
    **fields: Any,
) -> dict[str, Any]:
    """Create the bounded run-debug projection used by operations tooling."""

    return safe_diagnostics(
        {
            "run_id": run_id,
            "status": status,
            "stages": list(stages),
            "provider_calls": list(provider_calls),
            "blockers": list(blockers),
            "cost_usd": cost_usd,
            **fields,
        }
    )


__all__ = ["lineage_event", "safe_diagnostics", "safe_run_debug"]
