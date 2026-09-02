"""Disclosure sample gates and cohort-aware business-score contracts."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "scoring_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _symbol(module_name: str, name: str) -> Any:
    try:
        return getattr(import_module(module_name), name)
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"missing scoring contract: {module_name}.{name} ({error})", pytrace=False)


def _field(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, dict) else getattr(value, name, None)


@pytest.mark.parametrize("case", _cases()["disclosure_cases"], ids=lambda case: case["id"])
def test_disclosure_reliability_has_sample_coverage_gate_and_reason(case: dict[str, Any]) -> None:
    score_disclosure = _symbol("app.domain.scoring.disclosure", "score_disclosure_reliability")
    result = score_disclosure(case["claims"])
    assert _field(result, "state") == case["expected_state"]
    assert _field(result, "coverage") is not None
    assert _field(result, "sample_size") == len(case["claims"])
    assert _field(result, "score_version")
    assert _field(result, "explanation")
    assert "trustworthiness" not in str(_field(result, "label")).casefold()
    if case.get("expected_badge"):
        assert case["expected_badge"] in str(_field(result, "badges"))


@pytest.mark.parametrize("case", _cases()["business_cases"], ids=lambda case: case["id"])
def test_business_score_is_cohort_aware_and_treats_missing_data_as_unknown(
    case: dict[str, Any],
) -> None:
    score_business = _symbol("app.domain.scoring.business", "score_business")
    result = score_business(
        cohort=case["cohort"], stage=case.get("stage"), financials=case["financials"]
    )
    assert _field(result, "cohort") == case["expected_cohort"]
    assert _field(result, "score_version")
    assert _field(result, "breakdown")
    assert _field(result, "explanation")
    if case.get("expected_missing"):
        assert _field(result, "score") is None
        assert "COVERAGE" in str(_field(result, "state")).upper()


def test_public_and_startup_use_distinct_component_breakdowns() -> None:
    score_business = _symbol("app.domain.scoring.business", "score_business")
    public = score_business(
        cohort="PUBLIC", stage=None, financials={"revenue_growth": 0.2, "margin": 0.18}
    )
    startup = score_business(
        cohort="STARTUP",
        stage="SEED",
        financials={"revenue_growth": 4.0, "revenue_base": 1000, "traction": 0.4},
    )
    assert _field(public, "cohort") != _field(startup, "cohort")
    assert set(_field(public, "breakdown")) != set(_field(startup, "breakdown"))
