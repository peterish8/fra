from __future__ import annotations

from collections.abc import Mapping
from typing import Any

WATCHLIST_SCORE_VERSION = "watchlist-v1"


def score_candidate(
    candidate: Mapping[str, Any], *, score_version: str = WATCHLIST_SCORE_VERSION
) -> dict[str, Any]:
    signals = (
        candidate.get("signals", {}) if isinstance(candidate.get("signals", {}), Mapping) else {}
    )
    components = {
        "momentum": float(signals.get("momentum", 0) or 0),
        "traction": float(signals.get("traction", 0) or 0),
        "market": float(signals.get("market", 0) or 0),
        "resilience": float(signals.get("resilience", 0) or 0),
        "evidence": min(1.0, max(0.0, float(candidate.get("evidence_coverage", 0) or 0))),
        "disclosure": float(signals.get("disclosure", 0) or 0),
        "freshness": float(signals.get("freshness", 0) or 0),
    }
    weights = {
        "momentum": 0.3,
        "traction": 0.2,
        "market": 0.15,
        "resilience": 0.1,
        "evidence": 0.1,
        "disclosure": 0.1,
        "freshness": 0.05,
    }
    score = round(sum(components[key] * weight for key, weight in weights.items()) * 100, 3)
    return {
        "company_id": str(candidate.get("company_id", "")),
        "score": score,
        "score_version": score_version,
        "breakdown": components,
        "eligibility": {"evidence_coverage": components["evidence"]},
    }
