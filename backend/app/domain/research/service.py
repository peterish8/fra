"""Resumable, idempotent, budget-aware research-run orchestration."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.jobs.idempotency import IdempotencyResult, IdempotencyStore

from .models import (
    BudgetDecision,
    BudgetUsage,
    ResearchBudget,
    ResearchRun,
    ResearchRunRequest,
    ResearchRunStage,
    RunStage,
    RunStatus,
    StageStatus,
    StageTransition,
    now_utc,
)
from .repository import (
    InMemoryResearchRunRepository,
    ResearchRunNotFoundError,
    ResearchRunRepository,
    ResearchRunStateError,
)

_STAGES = tuple(RunStage)


class DuplicateReportVersionError(ResearchRunStateError):
    """A second report version was requested for the same run."""


class ResearchRunService:
    """Application-facing lifecycle boundary independent of HTTP and SQL.

    ``repository`` is expected to be backed by PostgreSQL in production.  The
    default repository is useful for a local worker and preserves the same
    checkpoint ordering and idempotency semantics.
    """

    def __init__(
        self,
        repository: ResearchRunRepository | None = None,
        *,
        idempotency: IdempotencyStore[ResearchRun] | None = None,
    ) -> None:
        self.repository = repository or InMemoryResearchRunRepository()
        self.idempotency = idempotency or IdempotencyStore[ResearchRun]()

    def create_run(
        self,
        request: ResearchRunRequest | Mapping[str, Any] | None = None,
        *,
        report_id: UUID | None = None,
        owner_user_id: str | None = None,
        trigger_type: str = "USER",
        requested_depth: str = "STANDARD",
        config_version: str = "config-v1",
        prompt_bundle_version: str = "prompt-v1",
        budget: ResearchBudget | Mapping[str, Any] | None = None,
        focus: tuple[str, ...] | list[str] = (),
        idempotency_key: str | None = None,
    ) -> ResearchRun:
        """Create a queued run, or return the original idempotent run."""

        validated = self._request(
            request,
            report_id=report_id,
            owner_user_id=owner_user_id,
            trigger_type=trigger_type,
            requested_depth=requested_depth,
            config_version=config_version,
            prompt_bundle_version=prompt_bundle_version,
            budget=budget,
            focus=focus,
        )
        fingerprint = _fingerprint(validated)

        def factory() -> ResearchRun:
            run = ResearchRun(
                run_id=uuid4(),
                report_id=validated.report_id,
                owner_user_id=validated.owner_user_id,
                trigger_type=validated.trigger_type,
                requested_depth=validated.requested_depth,
                config_version=validated.config_version,
                prompt_bundle_version=validated.prompt_bundle_version,
                budget=validated.budget,
            )
            return self.repository.create_run(run)

        if idempotency_key is None:
            return factory()
        scope = f"research-run:{validated.owner_user_id}:{validated.report_id}"
        result = self.idempotency.get_or_create(
            scope=scope,
            key=idempotency_key,
            fingerprint=fingerprint,
            factory=factory,
        )
        return result.resource

    create = create_run

    def create_run_result(
        self,
        request: ResearchRunRequest | Mapping[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> IdempotencyResult[ResearchRun]:
        """Return the run plus whether this request created it."""

        validated = self._request(request)
        if idempotency_key is None:
            return IdempotencyResult(resource=self.create_run(validated), created=True)
        scope = f"research-run:{validated.owner_user_id}:{validated.report_id}"
        fingerprint = _fingerprint(validated)
        result = self.idempotency.get_or_create(
            scope=scope,
            key=idempotency_key,
            fingerprint=fingerprint,
            factory=lambda: self.create_run(validated),
        )
        return result

    def get_run(self, run_id: UUID) -> ResearchRun:
        run = self.repository.get_run(run_id)
        if run is None:
            raise ResearchRunNotFoundError(str(run_id))
        return run

    get = get_run

    def stages(self, run_id: UUID) -> tuple[ResearchRunStage, ...]:
        return tuple(self.repository.list_stages(run_id))

    def start(self, run_id: UUID, *, stage: RunStage = RunStage.PLANNING) -> ResearchRun:
        """Begin a queued run at the first pipeline stage."""

        if stage is not RunStage.PLANNING:
            raise ResearchRunStateError("a new run must begin at PLANNING")
        return self.repository.begin_run(run_id, stage, now_utc())

    start_run = start

    def start_stage(self, run_id: UUID, stage: RunStage | str | None = None) -> ResearchRun:
        """Resume the current queued stage after a worker restart."""

        run = self.get_run(run_id)
        if run.status is not RunStatus.RUNNING or run.current_stage is None:
            raise ResearchRunStateError("only a running run can resume a stage")
        expected = RunStage(stage) if stage is not None else run.current_stage
        if expected is not run.current_stage:
            raise ResearchRunStateError("requested stage is not the active run stage")
        records = {record.stage: record for record in self.repository.list_stages(run_id)}
        record = records.get(expected)
        if record is None:
            raise ResearchRunStateError("active stage checkpoint is missing")
        if record.status is StageStatus.COMPLETE:
            raise ResearchRunStateError("completed stage cannot be started again")
        return self.repository.begin_stage(run_id, expected, now_utc())

    def checkpoint_stage(
        self,
        run_id: UUID,
        checkpoint: Mapping[str, Any],
        *,
        stage: RunStage | str | None = None,
        next_stage: RunStage | str | None = None,
    ) -> StageTransition:
        """Persist output, then advance exactly once.

        The repository transaction writes the stage checkpoint before changing
        ``current_stage``. Replaying a completed stage is rejected instead of
        creating another downstream transition or report version.
        """

        run = self.get_run(run_id)
        active_stage = RunStage(stage) if stage is not None else run.current_stage
        if active_stage is None:
            raise ResearchRunStateError("run has no active stage")
        following = RunStage(next_stage) if next_stage is not None else _next_stage(active_stage)
        if following is active_stage:
            raise ResearchRunStateError("next stage must differ from active stage")
        stage_records = {record.stage: record for record in self.repository.list_stages(run_id)}
        current_record = stage_records.get(active_stage)
        if current_record is not None and current_record.status is StageStatus.QUEUED:
            self.repository.begin_stage(run_id, active_stage, now_utc())
        updated = self.repository.checkpoint_and_advance(
            run_id,
            active_stage,
            dict(checkpoint),
            following,
            now_utc(),
        )
        return StageTransition(
            run=updated,
            completed_stage=active_stage,
            next_stage=following,
            checkpoint_sequence=updated.checkpoint_sequence,
        )

    checkpoint_and_advance = checkpoint_stage

    def consume_budget(
        self,
        run_id: UUID,
        *,
        cost_usd: Decimal | int | float | str = Decimal("0"),
        pages: int = 0,
        searches: int = 0,
        deep_research_calls: int = 0,
        follow_up_loops: int = 0,
    ) -> BudgetDecision:
        """Reserve usage and mark useful partial state when a limit is crossed."""

        run = self.get_run(run_id)
        delta = BudgetUsage(
            cost_usd=cost_usd,
            pages=pages,
            searches=searches,
            deep_research_calls=deep_research_calls,
            follow_up_loops=follow_up_loops,
        )
        usage = BudgetUsage(
            cost_usd=run.usage.cost_usd + delta.cost_usd,
            pages=run.usage.pages + delta.pages,
            searches=run.usage.searches + delta.searches,
            deep_research_calls=run.usage.deep_research_calls + delta.deep_research_calls,
            follow_up_loops=run.usage.follow_up_loops + delta.follow_up_loops,
        )
        reason = _budget_reason(run.budget, usage)
        self.repository.update_usage(run_id, usage, now_utc())
        if reason is not None:
            error_code = "COST_BUDGET_EXCEEDED" if reason == "COST_BUDGET_EXCEEDED" else reason
            self.repository.mark_terminal(
                run_id,
                status=RunStatus.PARTIAL,
                stage_status=StageStatus.PARTIAL,
                checkpoint={
                    "partial": True,
                    "reason": error_code,
                    "usage": usage.model_dump(mode="json"),
                },
                error_code=error_code,
                error_summary=error_code,
                when=now_utc(),
            )
        return BudgetDecision(allowed=reason is None, reason_code=reason, usage=usage)

    reserve_budget = consume_budget

    def fail(
        self,
        run_id: UUID,
        error_summary: str,
        *,
        error_code: str = "RESEARCH_FAILED",
    ) -> ResearchRun:
        return self.repository.mark_terminal(
            run_id,
            status=RunStatus.FAILED,
            stage_status=StageStatus.FAILED,
            checkpoint=None,
            error_code=error_code,
            error_summary=_safe_error(error_summary),
            when=now_utc(),
        )

    def cancel(self, run_id: UUID, reason: str = "cancelled by request") -> ResearchRun:
        return self.repository.mark_terminal(
            run_id,
            status=RunStatus.CANCELLED,
            stage_status=StageStatus.CANCELLED,
            checkpoint=None,
            error_code="RESEARCH_CANCELLED",
            error_summary=_safe_error(reason),
            when=now_utc(),
        )

    def attach_report_version(self, run_id: UUID, report_version_id: UUID | str) -> ResearchRun:
        version_id = UUID(str(report_version_id))
        run = self.get_run(run_id)
        if run.report_version_id is not None and run.report_version_id != version_id:
            raise DuplicateReportVersionError("a run already has a different report version")
        return self.repository.attach_report_version(run_id, version_id, now_utc())

    def ensure_report_version(
        self,
        run_id: UUID,
        factory: Callable[[], UUID | str],
    ) -> UUID:
        """Create at most one version for this run, returning the original ID."""

        run = self.get_run(run_id)
        if run.report_version_id is not None:
            return run.report_version_id
        version_id = UUID(str(factory()))
        return self.attach_report_version(run_id, version_id).report_version_id or version_id

    def resume(self, run_id: UUID) -> ResearchRun:
        """Return the durable checkpoint projection a restarted worker should use."""

        run = self.get_run(run_id)
        if run.status in {RunStatus.QUEUED, RunStatus.RUNNING}:
            return run
        return run

    def _request(
        self,
        request: ResearchRunRequest | Mapping[str, Any] | None,
        *,
        report_id: UUID | None = None,
        owner_user_id: str | None = None,
        trigger_type: str = "USER",
        requested_depth: str = "STANDARD",
        config_version: str = "config-v1",
        prompt_bundle_version: str = "prompt-v1",
        budget: ResearchBudget | Mapping[str, Any] | None = None,
        focus: tuple[str, ...] | list[str] = (),
    ) -> ResearchRunRequest:
        if request is not None:
            return (
                request
                if isinstance(request, ResearchRunRequest)
                else ResearchRunRequest.model_validate(request)
            )
        if report_id is None or owner_user_id is None:
            raise ValueError("report_id and owner_user_id are required")
        return ResearchRunRequest(
            report_id=report_id,
            owner_user_id=owner_user_id,
            trigger_type=trigger_type,
            requested_depth=requested_depth,
            config_version=config_version,
            prompt_bundle_version=prompt_bundle_version,
            budget=budget or ResearchBudget(),
            focus=tuple(focus),
        )


ResearchRunStateMachine = ResearchRunService
ResearchLifecycleService = ResearchRunService


def _next_stage(stage: RunStage) -> RunStage | None:
    try:
        index = _STAGES.index(stage)
    except ValueError as error:
        raise ResearchRunStateError(f"unknown research stage: {stage}") from error
    return _STAGES[index + 1] if index + 1 < len(_STAGES) else None


def _budget_reason(budget: ResearchBudget, usage: BudgetUsage) -> str | None:
    if budget.max_cost_usd is not None and usage.cost_usd > budget.max_cost_usd:
        return "COST_BUDGET_EXCEEDED"
    if budget.max_pages is not None and usage.pages > budget.max_pages:
        return "PAGE_LIMIT_EXCEEDED"
    if budget.max_searches is not None and usage.searches > budget.max_searches:
        return "SEARCH_LIMIT_EXCEEDED"
    if (
        budget.max_deep_research_calls is not None
        and usage.deep_research_calls > budget.max_deep_research_calls
    ):
        return "DEEP_RESEARCH_CALL_LIMIT_EXCEEDED"
    if (
        budget.max_follow_up_loops is not None
        and usage.follow_up_loops > budget.max_follow_up_loops
    ):
        return "FOLLOW_UP_LOOP_LIMIT_EXCEEDED"
    return None


def _fingerprint(request: ResearchRunRequest) -> str:
    serialized = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _safe_error(value: str) -> str:
    # Keep provider payloads/secrets out of durable error summaries.
    return " ".join(value.strip().split())[:1000] or "research failed"


__all__ = [
    "DuplicateReportVersionError",
    "ResearchLifecycleService",
    "ResearchRunService",
    "ResearchRunStateMachine",
]
