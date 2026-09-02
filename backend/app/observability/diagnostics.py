"""Secret-safe run diagnostics and structured lineage events."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_REDACT_KEYS = {"token", "api_key", "apikey", "authorization", "cookie", "prompt", "secret"}


def safe_diagnostics(event: Mapping[str, Any]) -> dict[str, Any]:
    def scrub(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): "[REDACTED]" if str(key).lower() in _REDACT_KEYS else scrub(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return scrub(dict(event))


def lineage_event(
    *,
    run_id: str,
    stage: str,
    status: str,
    provider: str | None = None,
    cost_usd: float = 0,
    **fields: Any,
) -> dict[str, Any]:
    return safe_diagnostics(
        {
            "run_id": run_id,
            "stage": stage,
            "status": status,
            "provider": provider,
            "cost_usd": cost_usd,
            **fields,
        }
    )
