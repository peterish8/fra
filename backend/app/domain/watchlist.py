"""Deterministic weekly watchlist eligibility and ranking."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def build_watchlist(
    candidates: Iterable[Mapping[str, Any]], *, minimum_evidence: float = 0.4
) -> dict[str, Any]:
    eligible = [
        dict(item)
        for item in candidates
        if item.get("entity_resolved", False)
        and not item.get("identity_collision", False)
        and float(item.get("evidence_coverage", 0) or 0) >= minimum_evidence
        and not item.get("critical_failure", False)
    ]
    ranked = sorted(eligible, key=lambda item: float(item.get("score", 0) or 0), reverse=True)
    return {
        "items": [{**item, "rank": index} for index, item in enumerate(ranked, 1)],
        "published": True,
        "count": len(ranked),
        "methodology_version": "watchlist-v1",
    }
