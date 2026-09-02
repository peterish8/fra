"""Source-family-aware benchmark with explicit false-positive/negative counts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.domain.sources.families import SourceFamilyClassifier, independent_family_count
from app.domain.sources.models import SourceRecord
from app.domain.verification.conflicts import classify_conflict

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "conflict_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _classification(value: Any) -> str:
    """Read the canonical class from a model or mapping without hiding errors."""

    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if not isinstance(value, dict):
        pytest.fail("conflict classifier returned a non-object result", pytrace=False)
    result = value.get("classification")
    if result is None:
        pytest.fail("conflict result is missing canonical classification", pytrace=False)
    return str(result)


def test_source_family_benchmark_reports_independence_not_url_count() -> None:
    for case in _cases()["family_benchmarks"]:
        sources = [
            SourceRecord(
                source_id=uuid4(),
                canonical_url=url,
                publisher="fixture",
                source_type="NEWS",
                authority_tier="C1",
            )
            for url in case["source_urls"]
        ]
        relationships = SourceFamilyClassifier().classify(
            sources,
            metadata={
                source.source_id: {"content_hash": case["content_hashes"][index]}
                for index, source in enumerate(sources)
            },
        )
        count = independent_family_count(
            [source.source_id for source in sources], relationships
        )
        assert count == case["expected_independent_families"], case["id"]
        # A provider can multiply URLs/observations without adding support.
        supports_conflict = count >= 2
        assert supports_conflict is case["expected_conflict_support"], case["id"]


def test_conflict_benchmark_reports_false_positive_and_negative_labels(
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected_conflict = {
        "NO_CONFLICT": False,
        "VALUE_CONFLICT": True,
        "DEFINITION_MISMATCH": False,
        "METHODOLOGY_DIFFERENCE": False,
        "GAAP_VS_NON_GAAP": False,
        "PERIOD_MISMATCH": False,
        "CURRENCY_MISMATCH": False,
        "SOURCE_DATE_MISMATCH": False,
        "ENTITY_SCOPE_DIFFERENCE": False,
        "RESTATEMENT": False,
    }
    labels = {case["expected_classification"] for case in _cases()["classification_cases"]}
    assert set(expected_conflict).issubset(labels)
    false_positive = false_negative = 0
    incorrect_classifications = 0
    for case in _cases()["classification_cases"]:
        output = classify_conflict(case["left"], case["right"])
        actual = _classification(output)
        if hasattr(output, "model_dump"):
            output_map = output.model_dump()
        else:
            output_map = output
        expected_label = case["expected_classification"]
        assert expected_label in expected_conflict, f"unlabeled benchmark class: {expected_label}"
        if expected_label == "NO_CONFLICT":
            assert (
                str(output_map.get("difference_classification"))
                == case["difference_classification"]
            )
        predicted = expected_conflict.get(actual, True)
        expected = expected_conflict[expected_label]
        false_positive += int(predicted and not expected)
        false_negative += int(expected and not predicted)
        incorrect_classifications += int(actual != expected_label)
    print(
        "conflict-benchmark: "
        f"cases={len(_cases()['classification_cases'])} "
        f"incorrect={incorrect_classifications} "
        f"false_positives={false_positive} false_negatives={false_negative}"
    )
    captured = capsys.readouterr().out
    assert "incorrect=" in captured
    assert "false_positives=" in captured
    assert "false_negatives=" in captured
    assert false_positive == 0
    assert false_negative == 0
    assert incorrect_classifications == 0


def test_conflict_benchmark_contains_required_mismatch_and_outcome_classes() -> None:
    labels = {case["expected_classification"] for case in _cases()["classification_cases"]}
    assert {
        "DEFINITION_MISMATCH",
        "METHODOLOGY_DIFFERENCE",
        "GAAP_VS_NON_GAAP",
        "PERIOD_MISMATCH",
        "CURRENCY_MISMATCH",
        "ENTITY_SCOPE_DIFFERENCE",
        "SOURCE_DATE_MISMATCH",
        "RESTATEMENT",
        "VALUE_CONFLICT",
        "NO_CONFLICT",
    } <= labels
    assert any(
        case["expected_classification"] == "VALUE_CONFLICT"
        for case in _cases()["classification_cases"]
    )
    assert any(
        case["expected_classification"] == "RESTATEMENT"
        for case in _cases()["classification_cases"]
    )
