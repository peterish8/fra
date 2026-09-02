"""Score breakdown DTO/API contracts expose separate explainable score families."""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest


def _symbol(module_name: str, name: str) -> Any:
    try:
        return getattr(import_module(module_name), name)
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"missing scoring API contract: {module_name}.{name} ({error})", pytrace=False)


def test_score_breakdown_dto_keeps_separate_versioned_drilldown_fields() -> None:
    dto_type = _symbol("app.api.scoring", "ScoreBreakdownResponse")
    result = dto_type.model_validate(
        {
            "company_id": "company-1",
            "research_confidence": {
                "score": 88,
                "score_version": "research-v1",
                "coverage": 1.0,
                "breakdown": {},
                "explanation": "Complete evidence.",
            },
            "evidence_coverage": {
                "score": 100,
                "score_version": "coverage-v1",
                "coverage": 1.0,
                "breakdown": {},
                "explanation": "All material claims assessed.",
            },
            "disclosure_reliability": {
                "state": "NOT_ENOUGH_DATA",
                "score": None,
                "score_version": "disclosure-v1",
                "coverage": 0.1,
                "breakdown": {},
                "explanation": "Sample is too small.",
            },
            "business_score": None,
        }
    )
    dumped = result.model_dump()
    assert set(dumped) >= {
        "company_id",
        "research_confidence",
        "evidence_coverage",
        "disclosure_reliability",
        "business_score",
    }
    assert "trust_score" not in dumped
    for family in ("research_confidence", "evidence_coverage", "disclosure_reliability"):
        assert dumped[family]["score_version"]
        assert "coverage" in dumped[family]
        assert "breakdown" in dumped[family]
        assert dumped[family]["explanation"]
