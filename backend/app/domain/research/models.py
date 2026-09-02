"""Typed durable research-run and stage contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunStage(StrEnum):
    PLANNING = "PLANNING"
    ENTITY_RESOLUTION = "ENTITY_RESOLUTION"
    RETRIEVING = "RETRIEVING"
    EXTRACTING = "EXTRACTING"
    VERIFYING = "VERIFYING"
    RESOLVING_CONFLICTS = "RESOLVING_CONFLICTS"
    FOLLOW_UP_RESEARCH = "FOLLOW_UP_RESEARCH"
    SCORING = "SCORING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETE = "COMPLETE"


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PARTIAL = "PARTIAL"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StageStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RunTrigger(StrEnum):
    USER = "USER"
    REFRESH = "REFRESH"
    WEEKLY = "WEEKLY"
    SYSTEM = "SYSTEM"


class ResearchDepth(StrEnum):
    FAST = "FAST"
    STANDARD = "STANDARD"
    DEEP = "DEEP"


class ResearchBudget(BaseModel):
    """Configuration limits for one run; ``None`` means no local limit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_cost_usd: Decimal | None = Field(default=None, ge=0)
    max_pages: int | None = Field(default=None, ge=0)
    max_searches: int | None = Field(default=None, ge=0)
    max_deep_research_calls: int | None = Field(default=None, ge=0)
    max_follow_up_loops: int | None = Field(default=None, ge=0)

    @field_validator("max_cost_usd", mode="before")
    @classmethod
    def normalize_cost(cls, value: Decimal | int | float | str | None) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))


class BudgetUsage(BaseModel):
    """Monotonic usage counters recorded with every checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cost_usd: Decimal = Field(default=Decimal("0"), ge=0)
    pages: int = Field(default=0, ge=0)
    searches: int = Field(default=0, ge=0)
    deep_research_calls: int = Field(default=0, ge=0)
    follow_up_loops: int = Field(default=0, ge=0)

    @field_validator("cost_usd", mode="before")
    @classmethod
    def normalize_cost(cls, value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value))


class ResearchRunRequest(BaseModel):
    """Validated immutable input used to create a run."""

    model_config = ConfigDict(extra="forbid")

    report_id: UUID
    owner_user_id: str = Field(min_length=1)
    trigger_type: RunTrigger = RunTrigger.USER
    requested_depth: ResearchDepth = ResearchDepth.STANDARD
    config_version: str = Field(default="config-v1", min_length=1, max_length=80)
    prompt_bundle_version: str = Field(default="prompt-v1", min_length=1, max_length=80)
    budget: ResearchBudget = Field(default_factory=ResearchBudget)
    focus: tuple[str, ...] = ()

    @field_validator("owner_user_id")
    @classmethod
    def normalize_owner(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("owner_user_id must not be blank")
        return value

    @field_validator("focus")
    @classmethod
    def normalize_focus(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        result = tuple(value.strip() for value in values)
        if any(not value for value in result):
            raise ValueError("focus values must not be blank")
        return result


class ResearchRun(BaseModel):
    """Current durable projection of one research execution."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    run_id: UUID = Field(default_factory=uuid4)
    report_id: UUID
    owner_user_id: str = Field(min_length=1)
    trigger_type: RunTrigger = RunTrigger.USER
    requested_depth: ResearchDepth = ResearchDepth.STANDARD
    status: RunStatus = RunStatus.QUEUED
    current_stage: RunStage | None = None
    config_version: str = Field(min_length=1, max_length=80)
    prompt_bundle_version: str = Field(min_length=1, max_length=80)
    budget: ResearchBudget = Field(default_factory=ResearchBudget)
    usage: BudgetUsage = Field(default_factory=BudgetUsage)
    checkpoint_sequence: int = Field(default=0, ge=0)
    error_code: str | None = None
    error_summary: str | None = None
    partial_reason: str | None = None
    report_version_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def research_run_id(self) -> UUID:
        return self.run_id


class ResearchRunStage(BaseModel):
    """Append-safe stage record; checkpoint is persisted before transition."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    run_id: UUID
    stage: RunStage
    status: StageStatus = StageStatus.QUEUED
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    checkpoint_sequence: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class BudgetDecision(BaseModel):
    """Result of attempting to reserve one unit of run budget."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool
    reason_code: str | None = None
    usage: BudgetUsage


class StageTransition(BaseModel):
    """Audit-friendly result of a checkpoint and stage transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run: ResearchRun
    completed_stage: RunStage
    next_stage: RunStage | None
    checkpoint_sequence: int


def now_utc() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "BudgetDecision",
    "BudgetUsage",
    "ResearchBudget",
    "ResearchDepth",
    "ResearchRun",
    "ResearchRunRequest",
    "ResearchRunStage",
    "RunStage",
    "RunStatus",
    "RunTrigger",
    "StageStatus",
    "StageTransition",
    "now_utc",
]
