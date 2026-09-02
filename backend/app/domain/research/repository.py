"""Persistence boundary for research runs and checkpoint transactions."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from .models import ResearchRun, ResearchRunStage, RunStage, RunStatus, StageStatus


class ResearchRunNotFoundError(LookupError):
    """A requested run does not exist in the repository."""


class ResearchRunStateError(ValueError):
    """A run or stage transition violates the lifecycle contract."""


class ResearchRunRepository(Protocol):
    """Repository methods required by the lifecycle service.

    A PostgreSQL implementation must execute ``checkpoint_and_advance`` in a
    single transaction: insert/update the stage checkpoint first, then update
    the run projection and insert the next stage row.
    """

    def create_run(self, run: ResearchRun) -> ResearchRun: ...

    def get_run(self, run_id: UUID) -> ResearchRun | None: ...

    def list_stages(self, run_id: UUID) -> Sequence[ResearchRunStage]: ...

    def begin_run(self, run_id: UUID, stage: RunStage, when: datetime) -> ResearchRun: ...

    def begin_stage(self, run_id: UUID, stage: RunStage, when: datetime) -> ResearchRun: ...

    def checkpoint_and_advance(
        self,
        run_id: UUID,
        stage: RunStage,
        checkpoint: dict[str, Any],
        next_stage: RunStage | None,
        when: datetime,
    ) -> ResearchRun: ...

    def update_usage(self, run_id: UUID, usage: Any, when: datetime) -> ResearchRun: ...

    def mark_terminal(
        self,
        run_id: UUID,
        *,
        status: RunStatus,
        stage_status: StageStatus | None,
        checkpoint: dict[str, Any] | None,
        error_code: str | None,
        error_summary: str | None,
        when: datetime,
    ) -> ResearchRun: ...

    def attach_report_version(
        self, run_id: UUID, report_version_id: UUID, when: datetime
    ) -> ResearchRun: ...


class InMemoryResearchRunRepository:
    """Thread-safe reference repository used by local workers and tests.

    It mirrors the transaction ordering required of PostgreSQL and records
    operation names so crash/restart tests can assert checkpoint-before-
    transition behavior without relying on timing.
    """

    def __init__(self) -> None:
        self.runs: dict[UUID, ResearchRun] = {}
        self.stages: dict[tuple[UUID, RunStage], ResearchRunStage] = {}
        self.events: list[str] = []
        self._lock = threading.RLock()

    def create_run(self, run: ResearchRun) -> ResearchRun:
        with self._lock:
            if run.run_id in self.runs:
                raise ResearchRunStateError("research run already exists")
            self.runs[run.run_id] = run.model_copy(deep=True)
            return self._copy_run(run.run_id)

    def get_run(self, run_id: UUID) -> ResearchRun | None:
        with self._lock:
            return self._copy_run(run_id) if run_id in self.runs else None

    def list_stages(self, run_id: UUID) -> Sequence[ResearchRunStage]:
        with self._lock:
            if run_id not in self.runs:
                raise ResearchRunNotFoundError(str(run_id))
            return tuple(
                stage.model_copy(deep=True)
                for (candidate, _), stage in self.stages.items()
                if candidate == run_id
            )

    def begin_run(self, run_id: UUID, stage: RunStage, when: datetime) -> ResearchRun:
        with self._lock:
            run = self._require(run_id)
            if run.status is not RunStatus.QUEUED:
                raise ResearchRunStateError("only a queued run can be started")
            if run.current_stage is not None:
                raise ResearchRunStateError("queued run already has a current stage")
            run.status = RunStatus.RUNNING
            run.current_stage = stage
            run.started_at = when
            run.updated_at = when
            self.stages[(run_id, stage)] = ResearchRunStage(
                run_id=run_id,
                stage=stage,
                status=StageStatus.RUNNING,
                started_at=when,
            )
            self.events.append(f"transition:{run_id}:QUEUED->{stage}")
            return self._copy_run(run_id)

    def begin_stage(self, run_id: UUID, stage: RunStage, when: datetime) -> ResearchRun:
        with self._lock:
            run = self._require(run_id)
            self._assert_active_stage(run, stage)
            stage_record = self.stages.get((run_id, stage))
            if stage_record is None:
                raise ResearchRunStateError("active stage checkpoint is missing")
            if stage_record.status is StageStatus.COMPLETE:
                raise ResearchRunStateError("completed stage cannot be started again")
            if stage_record.status is StageStatus.QUEUED:
                stage_record.status = StageStatus.RUNNING
                stage_record.started_at = when
                self.events.append(f"transition:{run_id}:{stage}:QUEUED->RUNNING")
            return self._copy_run(run_id)

    def checkpoint_and_advance(
        self,
        run_id: UUID,
        stage: RunStage,
        checkpoint: dict[str, Any],
        next_stage: RunStage | None,
        when: datetime,
    ) -> ResearchRun:
        with self._lock:
            run = self._require(run_id)
            self._assert_active_stage(run, stage)
            stage_record = self.stages.get((run_id, stage))
            if stage_record is None or stage_record.status is not StageStatus.RUNNING:
                raise ResearchRunStateError("stage is not running")
            sequence = run.checkpoint_sequence + 1

            # Persist the completed checkpoint before touching the run stage.
            stage_record.checkpoint = dict(checkpoint)
            stage_record.checkpoint_sequence = sequence
            stage_record.status = StageStatus.COMPLETE
            stage_record.completed_at = when
            self.events.append(f"checkpoint:{run_id}:{stage}:{sequence}")

            run.checkpoint_sequence = sequence
            run.updated_at = when
            if next_stage is None:
                run.current_stage = RunStage.COMPLETE
                run.status = RunStatus.READY
                run.completed_at = when
            else:
                run.current_stage = next_stage
                run.status = RunStatus.RUNNING
                self.stages.setdefault(
                    (run_id, next_stage),
                    ResearchRunStage(run_id=run_id, stage=next_stage),
                )
            self.events.append(f"transition:{run_id}:{stage}->{run.current_stage}")
            return self._copy_run(run_id)

    def update_usage(self, run_id: UUID, usage: Any, when: datetime) -> ResearchRun:
        with self._lock:
            run = self._require(run_id)
            run.usage = usage.model_copy(deep=True)
            run.updated_at = when
            self.events.append(f"usage:{run_id}")
            return self._copy_run(run_id)

    def mark_terminal(
        self,
        run_id: UUID,
        *,
        status: RunStatus,
        stage_status: StageStatus | None,
        checkpoint: dict[str, Any] | None,
        error_code: str | None,
        error_summary: str | None,
        when: datetime,
    ) -> ResearchRun:
        with self._lock:
            run = self._require(run_id)
            if run.status in {
                RunStatus.READY,
                RunStatus.FAILED,
                RunStatus.CANCELLED,
                RunStatus.PARTIAL,
            }:
                if run.status is status and run.error_code == error_code:
                    return self._copy_run(run_id)
                raise ResearchRunStateError("terminal run cannot transition again")
            stage_record = (
                self.stages.get((run_id, run.current_stage)) if run.current_stage else None
            )
            if stage_record is not None and stage_status is not None:
                if checkpoint is not None:
                    stage_record.checkpoint = dict(checkpoint)
                    run.checkpoint_sequence += 1
                    stage_record.checkpoint_sequence = run.checkpoint_sequence
                    self.events.append(
                        f"checkpoint:{run_id}:{run.current_stage}:{run.checkpoint_sequence}"
                    )
                stage_record.status = stage_status
                stage_record.completed_at = when
            run.status = status
            run.error_code = error_code
            run.error_summary = error_summary
            run.partial_reason = error_summary if status is RunStatus.PARTIAL else None
            run.completed_at = when
            run.updated_at = when
            self.events.append(f"transition:{run_id}:terminal:{status}")
            return self._copy_run(run_id)

    def attach_report_version(
        self, run_id: UUID, report_version_id: UUID, when: datetime
    ) -> ResearchRun:
        with self._lock:
            run = self._require(run_id)
            if run.report_version_id is not None and run.report_version_id != report_version_id:
                raise ResearchRunStateError("a run cannot create duplicate report versions")
            run.report_version_id = report_version_id
            run.updated_at = when
            self.events.append(f"report-version:{run_id}:{report_version_id}")
            return self._copy_run(run_id)

    def _require(self, run_id: UUID) -> ResearchRun:
        run = self.runs.get(run_id)
        if run is None:
            raise ResearchRunNotFoundError(str(run_id))
        return run

    def _assert_active_stage(self, run: ResearchRun, stage: RunStage) -> None:
        if run.status is not RunStatus.RUNNING or run.current_stage is not stage:
            raise ResearchRunStateError("stage is not the active run stage")

    def _copy_run(self, run_id: UUID) -> ResearchRun:
        return self.runs[run_id].model_copy(deep=True)


__all__ = [
    "InMemoryResearchRunRepository",
    "ResearchRunNotFoundError",
    "ResearchRunRepository",
    "ResearchRunStateError",
]
