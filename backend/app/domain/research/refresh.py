"""Bounded refresh planning that preserves prior report history."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def plan_refresh(claims: Iterable[Mapping[str, Any]], *, mode: str = "FULL") -> dict[str, Any]:
    normalized = mode.upper()
    if normalized not in {"FULL", "AFFECTED_ONLY"}:
        raise ValueError("mode must be FULL or AFFECTED_ONLY")
    records = list(claims)
    selected = (
        records
        if normalized == "FULL"
        else [
            item
            for item in records
            if item.get("affected") or item.get("stale") or item.get("conflicted")
        ]
    )
    return {
        "mode": normalized,
        "selected_claim_ids": [
            str(item.get("claim_id")) for item in selected if item.get("claim_id")
        ],
        "count": len(selected),
        "preserve_previous_version": True,
    }


__all__ = ["plan_refresh"]
