"""Claim freshness transitions and stale-target refresh contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "research_cases.json"
NOW = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


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
    pytest.fail(f"missing freshness contract: {module_name}.{name} ({error})", pytrace=False)


def _state(value: Any) -> str:
    if isinstance(value, str):
        return value
    state = getattr(value, "state", None)
    return str(state if state is not None else value)


@pytest.mark.parametrize("case", _cases()["freshness_cases"], ids=lambda case: case["id"])
def test_freshness_policy_marks_claim_state_by_type_and_age(case: dict[str, Any]) -> None:
    threshold_type = _symbol("app.domain.sources.freshness", "FreshnessThreshold")
    policy_type = _symbol("app.domain.sources.freshness", "FreshnessPolicy")
    evaluate = _symbol("app.domain.sources.freshness", "evaluate_freshness")
    policy = policy_type(
        by_claim_type={
            "CUSTOMER_COUNT": threshold_type(
                aging_after_days=90, stale_after_days=180, invalidate_after_days=None
            )
        }
    )
    result = evaluate(
        case["claim_type"], NOW - timedelta(days=case["age_days"]), evaluated_at=NOW,
        policy=policy,
        invalidated=case.get("invalidated", False),
    )
    assert _state(result) == case["expected_state"]


def test_stale_targeting_returns_only_affected_claims_and_preserves_history() -> None:
    threshold_type = _symbol("app.domain.sources.freshness", "FreshnessThreshold")
    policy_type = _symbol("app.domain.sources.freshness", "FreshnessPolicy")
    select = _symbol("app.domain.sources.freshness", "select_affected_claims")
    policy = policy_type(
        by_claim_type={
            "CUSTOMER_COUNT": threshold_type(
                aging_after_days=90, stale_after_days=180, invalidate_after_days=None
            )
        }
    )
    claims = [
        {
            "claim_id": "annual-current",
            "claim_type": "ANNUAL_REVENUE",
            "retrieved_at": NOW - timedelta(days=30),
        },
        {
            "claim_id": "customer-stale",
            "claim_type": "CUSTOMER_COUNT",
            "retrieved_at": NOW - timedelta(days=500),
            "history": ["claim-customer-original"],
        },
    ]
    targeted = select(claims, evaluated_at=NOW, policy=policy)
    ids = {item.claim_id for item in targeted}
    assert ids == {"customer-stale"}
    assert claims[1]["history"] == ["claim-customer-original"]
