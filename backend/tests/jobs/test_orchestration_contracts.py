"""Durable research-run checkpoint, budget, idempotency, and version contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.domain.research.models import ResearchBudget, RunStage
from app.domain.research.service import DuplicateReportVersionError, ResearchRunService

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "job_cases.json"
REPORT_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def _service() -> ResearchRunService:
    return ResearchRunService()


def _run(
    service: ResearchRunService,
    *,
    report_id: UUID = REPORT_ID,
    key: str = "run-1",
    budget: ResearchBudget | None = None,
) -> Any:
    return service.create_run(
        report_id=report_id,
        owner_user_id="owner-1",
        idempotency_key=key,
        budget=budget or ResearchBudget(max_cost_usd=10),
    )


def test_idempotent_trigger_replays_one_research_run() -> None:
    service = _service()
    first = _run(service, key="refresh-1")
    replay = _run(service, key="refresh-1")
    assert _field(replay, "run_id") == _field(first, "run_id")

    with pytest.raises((ValueError, RuntimeError)):
        service.create_run(
            report_id=REPORT_ID,
            owner_user_id="owner-1",
            idempotency_key="refresh-1",
            budget=ResearchBudget(max_cost_usd=20),
        )


def test_checkpoint_survives_worker_crash_and_resume() -> None:
    service = _service()
    run = _run(service, key="run-checkpoint")
    run_id = _field(run, "run_id")
    checkpoint_case = _cases()["research_cases"]["checkpoint"]
    service.start(run_id, stage=RunStage.PLANNING)
    service.checkpoint_stage(
        run_id,
        {"planned": True},
        stage=RunStage.PLANNING,
        next_stage=RunStage.RETRIEVING,
    )
    service.checkpoint_stage(
        run_id,
        checkpoint_case["checkpoint"],
        stage=RunStage.RETRIEVING,
        next_stage=RunStage.EXTRACTING,
    )
    stage_record = next(
        stage for stage in service.stages(run_id) if _field(stage, "stage") == RunStage.RETRIEVING
    )
    assert _field(stage_record, "checkpoint") == checkpoint_case["checkpoint"]

    resumed = service.resume(run_id)
    assert _field(resumed, "current_stage") == RunStage.EXTRACTING
    assert _field(resumed, "status") not in {"FAILED", "CANCELLED"}


def test_budget_exhaustion_preserves_partial_state() -> None:
    service = _service()
    budget_case = _cases()["research_cases"]["budget"]
    run = _run(
        service,
        report_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        key="run-budget",
        budget=ResearchBudget(max_cost_usd=budget_case["max_cost_usd"]),
    )
    run_id = _field(run, "run_id")
    service.start(run_id, stage=RunStage.PLANNING)
    service.checkpoint_stage(
        run_id,
        {"completed": ["entity_resolution"]},
        stage=RunStage.PLANNING,
        next_stage=RunStage.RETRIEVING,
    )
    decision = service.consume_budget(run_id, cost_usd=budget_case["stage_cost_usd"])
    result = service.get_run(run_id)
    assert decision.allowed is False
    assert _field(result, "status") == "PARTIAL"
    assert _field(result, "error_code") == budget_case["error_code"]
    assert _field(result, "current_stage") == RunStage.RETRIEVING
    assert service.stages(run_id)[-1].checkpoint["partial"] is True


def test_repeated_version_attachment_does_not_duplicate_report_version() -> None:
    service = _service()
    run = _run(
        service,
        report_id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        key="run-version",
    )
    run_id = _field(run, "run_id")
    version_id = uuid4()
    first = service.attach_report_version(run_id, version_id)
    replay = service.attach_report_version(run_id, version_id)
    assert _field(replay, "report_version_id") == _field(first, "report_version_id")
    with pytest.raises(DuplicateReportVersionError):
        service.attach_report_version(run_id, uuid4())


def test_checkpoint_is_persisted_before_stage_transition() -> None:
    service = _service()
    run = _run(
        service,
        report_id=UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
        key="run-order",
    )
    run_id = _field(run, "run_id")
    service.start(run_id, stage=RunStage.PLANNING)
    result = service.checkpoint_stage(
        run_id,
        {"source_cursor": "source-7", "facts_written": 3},
        stage=RunStage.PLANNING,
        next_stage=RunStage.ENTITY_RESOLUTION,
    )
    assert _field(result, "checkpoint_sequence") == 1
    events = service.repository.events
    assert events.index(f"checkpoint:{run_id}:PLANNING:1") < events.index(
        f"transition:{run_id}:PLANNING->ENTITY_RESOLUTION"
    )
