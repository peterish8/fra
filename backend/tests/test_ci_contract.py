"""Red contract for the documented pull-request quality workflow."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "ci_required_gates.json"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "quality.yml"


def _fixture() -> dict:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _workflow_text() -> str:
    assert WORKFLOW_PATH.is_file(), (
        "quality workflow is missing: expected .github/workflows/quality.yml"
    )
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_quality_workflow_runs_on_pull_requests_and_pushes() -> None:
    workflow = _workflow_text().lower()
    assert re.search(r"\bon:\s*", workflow)
    assert re.search(r"\bpull_request\s*:", workflow)
    assert re.search(r"\bpush\s*:", workflow)


@pytest.mark.parametrize("gate", list(_fixture()))
def test_quality_workflow_names_every_documented_gate(gate: str) -> None:
    workflow = _workflow_text().lower()
    contract = _fixture()[gate]
    for marker in contract["name_markers"]:
        assert marker.lower() in workflow, f"workflow does not name the {gate} gate"
    alternatives = [alternative.lower() for alternative in contract.get("alternatives", [])]
    if alternatives:
        assert any(alternative in workflow for alternative in alternatives), (
            f"workflow does not contain a runnable {gate} gate"
        )
    for command in contract.get("commands", []):
        assert command.lower() in workflow, f"workflow omits documented command {command!r}"


def test_quality_workflow_has_no_default_live_paid_provider_requirement() -> None:
    workflow = _workflow_text()
    forbidden_provider_requirements = (
        "PERPLEXITY_API_KEY",
        "GEMINI_API_KEY",
        "FIRECRAWL_API_KEY",
        "EXA_API_KEY",
        "--live-provider",
        "--live-provider-tests",
        "provider_live",
    )
    for forbidden in forbidden_provider_requirements:
        assert forbidden.lower() not in workflow.lower(), (
            f"default CI must not require paid/live provider access ({forbidden})"
        )
