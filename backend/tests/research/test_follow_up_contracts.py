"""Bounded follow-up stopping and evidence-lineage contracts."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "research_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _symbol(module_name: str, name: str) -> Any:
    try:
        module = import_module(module_name)
        return getattr(module, name)
    except (ModuleNotFoundError, AttributeError) as error:
        _missing(module_name, name, error)


def _missing(module_name: str, name: str, error: BaseException) -> NoReturn:
    pytest.fail(f"missing follow-up contract: {module_name}.{name} ({error})", pytrace=False)


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


@pytest.mark.parametrize("case", _cases()["follow_up_cases"], ids=lambda case: case["id"])
def test_follow_up_stops_on_sufficiency_no_progress_budget_or_provider_degradation(
    case: dict[str, Any],
) -> None:
    loop_type = _symbol("app.domain.research.follow_up", "FollowUpLoop")
    gap_type = _symbol("app.domain.research.follow_up", "EvidenceGap")
    degraded_type = _symbol("app.domain.research.follow_up", "ProviderDegradedError")
    gap = gap_type(
        claim_id=f"claim-{case['id']}",
        claim_statement=f"The {case['id']} claim is supported.",
        reasons=tuple(case["gaps"]),
    )
    results = iter(case["results"])
    evidence_index = iter(range(1, 100))

    def retrieve(_query: Any) -> list[dict[str, Any]]:
        item = next(results, {})
        if item.get("provider_status") == "TEMPORARY_FAILURE":
            raise degraded_type("fixture provider degraded")
        if not item.get("new_evidence"):
            return []
        evidence_id = item.get("lineage_id", f"evidence-{next(evidence_index)}")
        return [{"evidence_id": evidence_id}]

    def verify(lineage: Any) -> bool:
        return case["id"] == "sufficient" and any(
            str(item.evidence_id) == "evidence-2" for item in lineage
        )

    result = loop_type(max_loops=case["max_loops"]).run(gap, retrieve, verify=verify)
    assert _field(result, "stop_reason") == case["expected_stop"]
    assert _field(result, "loop_count") <= case["max_loops"]

    if case["id"] == "sufficient":
        assert _field(result, "evidence_lineage")
        assert "evidence-2" in str(_field(result, "evidence_lineage"))
    if case["id"] in {"no_progress", "loop_budget", "provider_degraded"}:
        assert _field(result, "iterations") is not None


def test_follow_up_extends_lineage_without_rewriting_prior_evidence() -> None:
    loop_type = _symbol("app.domain.research.follow_up", "FollowUpLoop")
    gap_type = _symbol("app.domain.research.follow_up", "EvidenceGap")
    evidence_type = _symbol("app.domain.research.follow_up", "EvidenceReference")
    result = loop_type(max_loops=2).run(
        gap_type(
            claim_id="claim-lineage",
            claim_statement="The lineage claim is supported.",
            reasons=("UNSUPPORTED",),
            evidence=(evidence_type(evidence_id="evidence-original", claim_id="claim-lineage"),),
        ),
        lambda _query: [{"evidence_id": "evidence-new"}],
    )
    lineage = str(_field(result, "evidence_lineage"))
    assert "evidence-original" in lineage
    assert "evidence-new" in lineage
