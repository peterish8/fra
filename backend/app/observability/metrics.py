"""Dependency-free metrics primitives for API, worker and provider telemetry."""

from __future__ import annotations

import math
import re
import threading
from collections.abc import Mapping

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,127}$")


def _metric_name(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_")
    if not _NAME_PATTERN.fullmatch(normalized):
        raise ValueError(f"invalid metric name: {name!r}")
    return normalized


def _labels(labels: Mapping[str, str] | None) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)[:100]) for key, value in (labels or {}).items()))


class MetricsRegistry:
    """Thread-safe in-process counters and bounded observations.

    A production exporter may periodically scrape ``snapshot`` or
    ``prometheus``; keeping the collection boundary local makes fixture tests
    deterministic and avoids introducing a mandatory telemetry dependency.
    """

    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._observations: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}
        self._lock = threading.RLock()

    def increment(
        self,
        name: str,
        value: float = 1.0,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        metric = _metric_name(name)
        if not math.isfinite(value) or value < 0:
            raise ValueError("counter increment must be finite and non-negative")
        key = (metric, _labels(labels))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        metric = _metric_name(name)
        if not math.isfinite(value) or value < 0:
            raise ValueError("observation must be finite and non-negative")
        key = (metric, _labels(labels))
        with self._lock:
            values = self._observations.setdefault(key, [])
            values.append(value)
            del values[:-500]

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        """Return counts and p50/p95/max observations without mutable state."""

        with self._lock:
            counters = {
                _format_key(name, labels): round(value, 8)
                for (name, labels), value in self._counters.items()
            }
            observations: dict[str, float | int] = {}
            for (name, labels), values in self._observations.items():
                if not values:
                    continue
                prefix = _format_key(name, labels)
                observations[f"{prefix}_count"] = len(values)
                observations[f"{prefix}_p50_ms"] = round(_percentile(values, 0.5), 2)
                observations[f"{prefix}_p95_ms"] = round(_percentile(values, 0.95), 2)
                observations[f"{prefix}_max_ms"] = round(max(values), 2)
            return {"counters": counters, "observations": observations}

    def prometheus(self) -> str:
        """Render a small text exposition suitable for an internal scrape."""

        snapshot = self.snapshot()
        lines = [f"{name} {value}" for name, value in snapshot["counters"].items()]
        lines.extend(f"{name} {value}" for name, value in snapshot["observations"].items())
        return "\n".join(lines) + ("\n" if lines else "")


def _format_key(name: str, labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return name
    safe_labels = ",".join(f'{key}="{value.replace(chr(34), "")}"' for key, value in labels)
    return f"{name}{{{safe_labels}}}"


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile)))
    return ordered[index]


__all__ = ["MetricsRegistry"]
