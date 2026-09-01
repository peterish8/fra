"""Formula-versioned calculation contracts."""

from __future__ import annotations

import json
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "financial_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _symbol(*names: str) -> Any:
    for module_name in (
        "app.domain.financial.calculations",
        "app.domain.financial.calculators",
        "app.domain.financial.normalization",
    ):
        try:
            module = import_module(module_name)
        except ModuleNotFoundError:
            continue
        for name in names:
            if hasattr(module, name):
                return getattr(module, name)
    _missing(" or ".join(names))


def _missing(name: str) -> NoReturn:
    pytest.fail(f"missing financial calculation contract: {name}", pytrace=False)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump()
    pytest.fail("financial calculator returned a non-object result", pytrace=False)


@pytest.mark.parametrize("case", _cases()["calculation_cases"], ids=lambda case: case["id"])
def test_derived_formulas_are_deterministic_and_versioned(case: dict[str, Any]) -> None:
    if case["operation"] == "growth":
        calculate = _symbol("calculate_growth")
        result = calculate(case["current"], case["prior"])
    elif case["operation"] == "margin":
        calculate = _symbol("calculate_margin")
        result = calculate(case["numerator"], case["denominator"])
    elif case["operation"] == "ratio":
        calculate = _symbol("calculate_ratio")
        result = calculate(case["numerator"], case["denominator"])
    else:
        compare = _symbol("within_tolerance")
        result = compare(
            Decimal(str(case["left"])), Decimal(str(case["right"])), metric="revenue"
        )
        assert result is case["expected"]
        return
    output = _mapping(result)
    if case.get("expected_error"):
        assert str(output["status"]) == {
            "DIVIDE_BY_ZERO": "DIVIDE_BY_ZERO",
            "INSUFFICIENT_DATA": "NOT_REPORTED",
        }[case["expected_error"]]
        assert output["output"] is None
        return
    assert float(output["output"]) == pytest.approx(case["expected"])
    assert output.get("formula") or output.get("formula_code")
    assert output.get("formula_version") or output.get("version")
    assert output.get("inputs")
