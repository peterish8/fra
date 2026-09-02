"""Typed durable-job records and retry policy primitives."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobErrorClass(StrEnum):
    RETRYABLE = "RETRYABLE"
    PERMANENT = "PERMANENT"
    CANCELLED = "CANCELLED"


class RetryPolicy(BaseModel):
    """Bounded exponential retry settings.

    ``jitter_ratio`` is applied by the queue using an injected random source;
    keeping it in the policy makes scheduling deterministic in tests without
    putting randomness in persistence.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    base_delay_seconds: float = Field(default=1.0, ge=0)
    max_delay_seconds: float = Field(default=300.0, ge=0)
    jitter_ratio: float = Field(default=0.2, ge=0, le=1)

    def delay_seconds(self, attempt_count: int, jitter: float = 0.0) -> float:
        if attempt_count < 1:
            attempt_count = 1
        exponential = min(
            self.max_delay_seconds,
            self.base_delay_seconds * (2 ** (attempt_count - 1)),
        )
        bounded_jitter = max(-1.0, min(1.0, jitter)) * self.jitter_ratio
        return max(0.0, min(self.max_delay_seconds, exponential * (1 + bounded_jitter)))


class JobRecord(BaseModel):
    """The durable state needed to safely resume a worker attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    id: UUID = Field(
        default_factory=uuid4,
        validation_alias=AliasChoices("id", "job_id"),
        serialization_alias="id",
    )
    job_type: str = Field(min_length=1, max_length=160)
    idempotency_key: str = Field(min_length=1, max_length=500)
    status: JobStatus = JobStatus.QUEUED
    priority: int = 100
    payload: dict[str, Any] = Field(default_factory=dict)
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=5, ge=1)
    available_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    lease_until: datetime | None = None
    leased_by: str | None = Field(default=None, max_length=200)
    last_error: str | None = Field(default=None, max_length=2000)
    result: dict[str, Any] | None = None
    provider_request_id: str | None = Field(default=None, max_length=500)
    research_run_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def job_id(self) -> UUID:
        return self.id

    @field_validator("idempotency_key", "job_type", "leased_by", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> Any:
        if value is None:
            return value
        return value.strip() if isinstance(value, str) else value

    def is_lease_expired(self, now: datetime) -> bool:
        return self.status is JobStatus.RUNNING and (
            self.lease_until is None or self.lease_until <= now
        )


class JobLease(BaseModel):
    """Claim response for callers that want an explicit lease envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job: JobRecord
    worker_id: str = Field(min_length=1, max_length=200)
    lease_until: datetime

    @property
    def job_id(self) -> UUID:
        return self.job.id


class EnqueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    job_type: str = Field(min_length=1, max_length=160)
    idempotency_key: str = Field(min_length=1, max_length=500)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 100
    max_attempts: int = Field(default=5, ge=1)
    available_at: datetime | None = None
    research_run_id: UUID | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def lease_deadline(now: datetime, lease_seconds: float) -> datetime:
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    return ensure_utc(now) + timedelta(seconds=lease_seconds)


__all__ = [
    "EnqueueRequest",
    "JobErrorClass",
    "JobLease",
    "JobRecord",
    "JobStatus",
    "RetryPolicy",
    "ensure_utc",
    "lease_deadline",
    "utc_now",
]
