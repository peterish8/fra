"""Immutable report-version and evidence-linked diff helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReportVersion:
    report_id: str
    version: int
    claim_version_ids: tuple[str, ...]
    score_snapshot_ids: tuple[str, ...] = ()
    status: str = "STAGED"


def create_version(
    report_id: str,
    version: int,
    claim_version_ids: list[str] | tuple[str, ...],
    *,
    score_snapshot_ids: list[str] | tuple[str, ...] = (),
) -> ReportVersion:
    if version < 1:
        raise ValueError("version must be positive")
    return ReportVersion(
        str(report_id),
        version,
        tuple(dict.fromkeys(map(str, claim_version_ids))),
        tuple(map(str, score_snapshot_ids)),
    )


def diff_versions(
    old: Mapping[str, Any] | None, new: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    before = old or {}
    changes = {
        key: []
        for key in (
            "unchanged",
            "added",
            "updated",
            "invalidated",
            "stale",
            "conflicted",
            "resolved",
            "score_changed",
        )
    }
    old_claims = before.get("claims", {}) if isinstance(before.get("claims", {}), Mapping) else {}
    new_claims = new.get("claims", {}) if isinstance(new.get("claims", {}), Mapping) else {}
    for claim_id, value in new_claims.items():
        if claim_id not in old_claims:
            changes["added"].append({"claim_id": claim_id, "new": value})
        elif old_claims[claim_id] == value:
            changes["unchanged"].append({"claim_id": claim_id})
        else:
            changes["updated"].append(
                {"claim_id": claim_id, "old": old_claims[claim_id], "new": value}
            )
    for claim_id, value in old_claims.items():
        if claim_id not in new_claims:
            changes["invalidated"].append({"claim_id": claim_id, "old": value})
    return changes


__all__ = ["ReportVersion", "create_version", "diff_versions"]
