"""Deterministic money, unit, period, sign, and FX contracts."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "financial_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _symbol(module_names: tuple[str, ...], *names: str) -> Any:
    errors: list[str] = []
    for module_name in module_names:
        try:
            module = import_module(module_name)
        except ModuleNotFoundError as error:
            errors.append(f"{module_name}: {error}")
            continue
        for name in names:
            if hasattr(module, name):
                return getattr(module, name)
    _missing(" or ".join(module_names), " or ".join(names), errors)


def _missing(module_name: str, name: str, errors: list[str]) -> NoReturn:
    pytest.fail(
        f"missing financial normalization contract {module_name}.{name}: {'; '.join(errors)}",
        pytrace=False,
    )


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump()
    pytest.fail("financial normalizer returned a non-object result", pytrace=False)


@pytest.mark.parametrize(
    "case", _cases()["normalization_cases"], ids=lambda case: case["id"]
)
def test_values_retain_originals_and_normalize_units_deterministically(
    case: dict[str, Any],
) -> None:
    normalize = _symbol(
        ("app.domain.financial.normalization", "app.domain.financial.normalizer"),
        "normalize_financial_value",
        "normalize_value",
        "normalize",
    )
    value = case["raw_value"] if case["id"] == "negative_parentheses" else case["numeric_value"]
    result = normalize(
        value,
        unit=case["unit"],
        currency=case.get("currency"),
    )
    output = _mapping(result)
    original = output.get("original_value", output.get("raw_value"))
    if case["numeric_value"] is None:
        assert original is None
    else:
        assert float(original) == pytest.approx(case["numeric_value"])
    actual_value = output.get("normalized_value", output.get("value"))
    if case["expected_value"] is not None:
        assert float(actual_value) == pytest.approx(case["expected_value"])
    else:
        assert actual_value is None
    assert output.get("normalized_unit", output.get("unit")) == case["expected_unit"]


@pytest.mark.parametrize(
    "case", _cases()["period_cases"], ids=lambda case: case["id"]
)
def test_period_labels_are_typed_before_comparison(case: dict[str, Any]) -> None:
    classify = _symbol(
        ("app.domain.financial.normalization", "app.domain.financial.normalizer"),
        "normalize_period",
        "classify_period",
    )
    result = classify(case["label"])
    output = _mapping(result)
    assert str(output.get("kind", output.get("period_kind"))) == case["expected_kind"]


@pytest.mark.parametrize(
    "case", _cases()["fx_cases"], ids=lambda case: case["id"]
)
def test_fx_requires_explicit_rate_and_date_and_preserves_currency_identity(
    case: dict[str, Any],
) -> None:
    convert = _symbol(
        ("app.domain.financial.normalization", "app.domain.financial.normalizer"),
        "normalize_financial_value",
    )
    kwargs = {
        "value": case["value"],
        "currency": case["currency"],
        "normalized_currency": case["target_currency"],
        "fx_rate": case["fx_rate"],
        "fx_date": case["fx_date"],
    }
    if case.get("expected_error"):
        with pytest.raises((ValueError, AssertionError)):
            convert(**kwargs)
        return
    output = _mapping(convert(**kwargs))
    assert output.get("normalized_currency") == case["target_currency"]
    assert output.get("value", output.get("normalized_value")) == pytest.approx(
        case["expected_value"]
    )
    assert str(output.get("fx_date")) == case["fx_date"]
