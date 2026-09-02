"""Deep-research eligibility and adversarial-query safety contracts."""

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
    pytest.fail(f"missing Phase 06-02 contract: {module_name}.{name} ({error})", pytrace=False)


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _items(value: Any, name: str) -> list[Any]:
    items = _field(value, name)
    if items is None:
        pytest.fail(f"research result is missing {name}", pytrace=False)
    return list(items)


@pytest.mark.parametrize("case", _cases()["routing_cases"], ids=lambda case: case["id"])
def test_deep_research_routes_only_eligible_work(case: dict[str, Any]) -> None:
    router_type = _symbol("app.providers.research.router", "DeepResearchRouter")
    adapter_type = _symbol(
        "app.providers.research.fixture", "FixtureDeepResearchAdapter"
    )
    adapter = adapter_type(
        payload={"evidence": [{"source_id": "fixture-source", "excerpt": "Candidate evidence."}]}
    )
    decision = router_type(adapter).route(case["request"])
    status = str(_field(decision, "status"))
    assert (status != "SKIPPED") is case["expected_eligible"]
    assert len(adapter.calls) == int(case["expected_eligible"])
    if not case["expected_eligible"]:
        assert _field(decision, "safe_metadata")["reason"]


def test_deep_research_result_is_non_authoritative() -> None:
    adapter_type = _symbol(
        "app.providers.research.fixture", "FixtureDeepResearchAdapter"
    )
    request_type = _symbol("app.providers.research.contracts", "DeepResearchRequest")
    adapter = adapter_type(
        provider="fixture",
        payload={
            "summary": "Candidate evidence.",
            "evidence": [{"source_id": "source-1", "excerpt": "Candidate evidence."}],
            "verdict": "VERIFIED",
        },
    )
    result = adapter.research(request_type(query="candidate evidence"))
    assert _field(result, "authoritative") is False
    assert _field(result, "verdict") is None
    assert "verdict" not in (_field(result, "data") or {})
    assert _field(result, "safe_metadata")["authoritative"] is False


def test_adversarial_planner_seeks_counterevidence_without_declaring_false() -> None:
    planner = _symbol("app.domain.verification.adversarial", "build_adversarial_plan")
    plan = planner(
        {
            "claim_id": "claim-revenue-1",
            "statement": "FY2026 revenue was $100 million.",
            "materiality": "HIGH",
        },
        evidence_gaps=[
            "newer", "definition", "market exit", "regulator", "restatement",
            "estimate", "counterexample",
        ],
        max_queries=8,
        unresolved=True,
    )
    assert _field(plan, "eligible") is True
    focuses = {str(_field(item, "focus")) for item in _items(plan, "queries")}
    assert focuses == {
        "CONTRADICTION", "NEWER_EVIDENCE", "DEFINITION_CHANGE", "MARKET_EXIT",
        "REGULATORY_ACTION", "RESTATEMENT", "ALTERNATIVE_ESTIMATE", "COUNTEREXAMPLE",
    }
    rendered = " ".join(str(item).casefold() for item in _items(plan, "queries"))
    assert "declare false" not in rendered
    assert "verdict" not in rendered


def test_adversarial_result_is_evidence_only() -> None:
    normalize = _symbol(
        "app.domain.verification.adversarial", "normalize_adversarial_result"
    )
    result = normalize(
        {
            "claim_id": "claim-1",
            "focus": "CONTRADICTION",
            "query": "find counterevidence",
            "outcome": "COUNTEREVIDENCE",
            "evidence": [{"excerpt": "An independent filing reports a lower value."}],
            "explanation": "Candidate evidence requires deterministic verification.",
            "verdict": "VERIFIED",
        }
    )
    assert _field(result, "authoritative") is False
    assert _field(result, "verdict") is None
