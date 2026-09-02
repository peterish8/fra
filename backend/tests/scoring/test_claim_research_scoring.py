"""Deterministic claim confidence, coverage, and research confidence contracts."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "scoring_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _symbol(module_name: str, name: str) -> Any:
    try:
        return getattr(import_module(module_name), name)
    except (ModuleNotFoundError, AttributeError) as error:
        _missing(module_name, name, error)


def _missing(module_name: str, name: str, error: BaseException) -> NoReturn:
    pytest.fail(f"missing scoring contract: {module_name}.{name} ({error})", pytrace=False)


def _field(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, dict) else getattr(value, name, None)


@pytest.mark.parametrize("case", _cases()["claim_cases"], ids=lambda case: case["id"])
def test_claim_confidence_is_deterministic_explainable_and_capped(case: dict[str, Any]) -> None:
    score_claim = _symbol("app.domain.scoring.claim_confidence", "score_claim_confidence")
    first = score_claim(
        dimensions=case["dimensions"],
        materiality=case["materiality"],
        conflict=case.get("conflict"),
        freshness=case.get("freshness"),
        identity_resolved=case.get("identity_resolved", True),
    )
    second = score_claim(
        dimensions=case["dimensions"],
        materiality=case["materiality"],
        conflict=case.get("conflict"),
        freshness=case.get("freshness"),
        identity_resolved=case.get("identity_resolved", True),
    )
    assert first == second
    score = float(_field(first, "score"))
    assert 0 <= score <= 100
    assert score <= case.get("expected_max", 100)
    assert score >= case.get("expected_min", 0)
    assert _field(first, "score_version")
    assert _field(first, "breakdown")
    assert _field(first, "explanation")
    assert "VERIFIED" not in str(_field(first, "verdict")).upper()


def test_na_dimensions_are_renormalized_not_penalized_as_zero() -> None:
    score_claim = _symbol("app.domain.scoring.claim_confidence", "score_claim_confidence")
    result = score_claim(
        dimensions={
            "semantic": 90,
            "authority": 90,
            "independence": 90,
            "numeric": None,
            "temporal": None,
            "agreement": 90,
            "freshness": 90,
            "adversarial": 90,
        },
        materiality="MEDIUM",
    )
    breakdown = _field(result, "breakdown")
    assert breakdown["numeric"]["state"] in {"N/A", "NOT_APPLICABLE"}
    assert breakdown["temporal"]["state"] in {"N/A", "NOT_APPLICABLE"}
    assert float(_field(result, "score")) > 80


@pytest.mark.parametrize("case", _cases()["research_cases"], ids=lambda case: case["id"])
def test_research_confidence_exposes_coverage_identity_and_gates(case: dict[str, Any]) -> None:
    score_research = _symbol("app.domain.scoring.research_confidence", "score_research_confidence")
    result = score_research(
        claims=case["claims"],
        identity_resolved=case["identity_resolved"],
        citation_coverage=case["citation_coverage"],
    )
    score = float(_field(result, "score"))
    assert score <= case.get("expected_max", 100)
    assert score >= case.get("expected_min", 0)
    assert _field(result, "coverage") is not None
    assert _field(result, "breakdown")
    assert _field(result, "explanation")
    if not case["identity_resolved"]:
        assert "IDENT" in str(_field(result, "breakdown")).upper()
