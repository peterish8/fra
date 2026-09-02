"""Durable job queue semantics with an in-memory and DB-API adapter.

``InMemoryJobQueue`` is a concurrency-safe reference implementation used by
local workers and tests. ``PostgresJobQueue`` keeps the same contract while
emitting transaction-safe SQL for the schema's ``jobs`` table. Domain stages
remain outside this module: queue state is only delivery state.
"""

from __future__ import annotations

import copy
import json
import random
import re
import threading
from collections.abc import Callable, Mapping, MutableSequence, Sequence
from datetime import datetime, timedelta
from typing import Any, Protocol, cast
from uuid import UUID

from .models import (
    EnqueueRequest,
    JobLease,
    JobRecord,
    JobStatus,
    RetryPolicy,
    ensure_utc,
    lease_deadline,
    utc_now,
)

JobRef = UUID | str | JobRecord | JobLease
Clock = Callable[[], datetime]
RandomSource = Callable[[], float]


class JobQueueError(RuntimeError):
    """Base exception for queue lifecycle violations."""


class IdempotencyConflictError(JobQueueError):
    """An idempotency key was reused for a different job request."""


class JobNotFoundError(JobQueueError):
    """The requested job does not exist."""


class LeaseLostError(JobQueueError):
    """A worker attempted to mutate a job it no longer leases."""


class InvalidJobTransitionError(JobQueueError):
    """A terminal or otherwise invalid job transition was requested."""


class JobQueue(Protocol):
    def enqueue(
        self,
        job_type: str | EnqueueRequest,
        idempotency_key: str | None = None,
        payload: Mapping[str, Any] | None = None,
        *,
        priority: int = 100,
        max_attempts: int = 5,
        available_at: datetime | None = None,
        research_run_id: UUID | None = None,
    ) -> JobRecord: ...

    def claim(
        self, worker_id: str, *, lease_seconds: float = 60, now: datetime | None = None
    ) -> JobRecord | None: ...

    def heartbeat(
        self,
        job: JobRef,
        worker_id: str,
        *,
        lease_seconds: float = 60,
        now: datetime | None = None,
    ) -> JobRecord: ...

    def complete(
        self,
        job: JobRef,
        worker_id: str,
        *,
        result: Mapping[str, Any] | None = None,
        provider_request_id: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord: ...

    def fail(
        self,
        job: JobRef,
        worker_id: str,
        error: BaseException | str,
        *,
        retryable: bool = True,
        provider_request_id: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord: ...

    def cancel(
        self,
        job: JobRef,
        *,
        worker_id: str | None = None,
        reason: str = "cancelled",
        now: datetime | None = None,
    ) -> JobRecord: ...

    def expire_leases(self, *, now: datetime | None = None) -> Sequence[JobRecord]: ...


class InMemoryJobQueue:
    """Atomic reference queue with the same transitions as the SQL adapter."""

    def __init__(
        self,
        *,
        retry_policy: RetryPolicy | None = None,
        clock: Clock = utc_now,
        random_source: RandomSource | None = None,
    ) -> None:
        self.retry_policy = retry_policy or RetryPolicy()
        self._clock = clock
        self._random = random_source or random.random
        self._jobs: dict[UUID, JobRecord] = {}
        self._idempotency: dict[str, tuple[str, UUID]] = {}
        self._lock = threading.RLock()

    @property
    def jobs(self) -> Mapping[UUID, JobRecord]:
        with self._lock:
            return dict(self._jobs)

    def enqueue(
        self,
        job_type: str | EnqueueRequest,
        idempotency_key: str | None = None,
        payload: Mapping[str, Any] | None = None,
        *,
        priority: int = 100,
        max_attempts: int = 5,
        available_at: datetime | None = None,
        research_run_id: UUID | None = None,
    ) -> JobRecord:
        request = _enqueue_request(
            job_type,
            idempotency_key,
            payload,
            priority=priority,
            max_attempts=max_attempts,
            available_at=available_at,
            research_run_id=research_run_id,
        )
        fingerprint = _fingerprint(request)
        now = ensure_utc(self._clock())
        with self._lock:
            prior = self._idempotency.get(request.idempotency_key)
            if prior is not None:
                old_fingerprint, old_id = prior
                if old_fingerprint != fingerprint:
                    raise IdempotencyConflictError(
                        "idempotency key was already used for a different job"
                    )
                return self._jobs[old_id]
            job = JobRecord(
                job_type=request.job_type,
                idempotency_key=request.idempotency_key,
                status=JobStatus.QUEUED,
                priority=request.priority,
                payload=copy.deepcopy(request.payload),
                max_attempts=request.max_attempts,
                available_at=ensure_utc(request.available_at or now),
                research_run_id=request.research_run_id,
                created_at=now,
                updated_at=now,
            )
            self._jobs[job.id] = job
            self._idempotency[request.idempotency_key] = (fingerprint, job.id)
            return job

    def get(self, job: JobRef) -> JobRecord:
        with self._lock:
            return self._get_locked(_job_id(job))

    def list(self, *, status: JobStatus | None = None) -> Sequence[JobRecord]:
        with self._lock:
            records = [job for job in self._jobs.values() if status is None or job.status is status]
        return sorted(records, key=lambda item: (item.created_at, str(item.id)))

    def claim(
        self, worker_id: str, *, lease_seconds: float = 60, now: datetime | None = None
    ) -> JobRecord | None:
        worker_id = _required_worker(worker_id)
        current = ensure_utc(now or self._clock())
        deadline = lease_deadline(current, lease_seconds)
        with self._lock:
            self._expire_locked(current)
            candidates = [
                job
                for job in self._jobs.values()
                if job.status is JobStatus.QUEUED and ensure_utc(job.available_at) <= current
            ]
            candidates.sort(
                key=lambda item: (
                    -item.priority,
                    ensure_utc(item.available_at),
                    ensure_utc(item.created_at),
                    str(item.id),
                )
            )
            for current_job in candidates:
                if current_job.attempt_count >= current_job.max_attempts:
                    self._replace(
                        current_job.model_copy(
                            update={
                                "status": JobStatus.FAILED,
                                "last_error": "maximum attempts exhausted",
                                "updated_at": current,
                            }
                        )
                    )
                    continue
                return self._replace(
                    current_job.model_copy(
                        update={
                            "status": JobStatus.RUNNING,
                            "attempt_count": current_job.attempt_count + 1,
                            "lease_until": deadline,
                            "leased_by": worker_id,
                            "updated_at": current,
                        }
                    )
                )
        return None

    def claim_lease(
        self, worker_id: str, *, lease_seconds: float = 60, now: datetime | None = None
    ) -> JobLease | None:
        job = self.claim(worker_id, lease_seconds=lease_seconds, now=now)
        return (
            JobLease(job=job, worker_id=worker_id, lease_until=cast(datetime, job.lease_until))
            if job is not None
            else None
        )

    def heartbeat(
        self,
        job: JobRef,
        worker_id: str,
        *,
        lease_seconds: float = 60,
        now: datetime | None = None,
    ) -> JobRecord:
        worker_id = _required_worker(worker_id)
        current = ensure_utc(now or self._clock())
        with self._lock:
            current_job = self._get_locked(_job_id(job))
            self._assert_lease(current_job, worker_id, current)
            return self._replace(
                current_job.model_copy(
                    update={
                        "lease_until": lease_deadline(current, lease_seconds),
                        "updated_at": current,
                    }
                )
            )

    def complete(
        self,
        job: JobRef,
        worker_id: str,
        *,
        result: Mapping[str, Any] | None = None,
        provider_request_id: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord:
        current = ensure_utc(now or self._clock())
        with self._lock:
            current_job = self._get_locked(_job_id(job))
            self._assert_lease(current_job, _required_worker(worker_id), current)
            return self._replace(
                current_job.model_copy(
                    update={
                        "status": JobStatus.SUCCEEDED,
                        "lease_until": None,
                        "leased_by": None,
                        "result": copy.deepcopy(dict(result)) if result is not None else None,
                        "provider_request_id": provider_request_id,
                        "updated_at": current,
                    }
                )
            )

    def fail(
        self,
        job: JobRef,
        worker_id: str,
        error: BaseException | str,
        *,
        retryable: bool = True,
        provider_request_id: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord:
        current = ensure_utc(now or self._clock())
        with self._lock:
            current_job = self._get_locked(_job_id(job))
            self._assert_lease(current_job, _required_worker(worker_id), current)
            safe_error = sanitize_error(error)
            should_retry = retryable and current_job.attempt_count < current_job.max_attempts
            update: dict[str, Any] = {
                "status": JobStatus.QUEUED if should_retry else JobStatus.FAILED,
                "lease_until": None,
                "leased_by": None,
                "last_error": safe_error,
                "provider_request_id": provider_request_id,
                "updated_at": current,
            }
            if should_retry:
                delay = self.retry_policy.delay_seconds(
                    current_job.attempt_count, self._random() * 2 - 1
                )
                update["available_at"] = current + timedelta(seconds=delay)
            return self._replace(current_job.model_copy(update=update))

    def cancel(
        self,
        job: JobRef,
        *,
        worker_id: str | None = None,
        reason: str = "cancelled",
        now: datetime | None = None,
    ) -> JobRecord:
        current = ensure_utc(now or self._clock())
        with self._lock:
            current_job = self._get_locked(_job_id(job))
            if current_job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
                raise InvalidJobTransitionError("terminal jobs cannot be cancelled")
            if current_job.status is JobStatus.RUNNING:
                if worker_id is None:
                    raise LeaseLostError("running jobs require their lease owner to cancel")
                self._assert_lease(current_job, _required_worker(worker_id), current)
            return self._replace(
                current_job.model_copy(
                    update={
                        "status": JobStatus.CANCELLED,
                        "lease_until": None,
                        "leased_by": None,
                        "last_error": sanitize_error(reason),
                        "updated_at": current,
                    }
                )
            )

    def expire_leases(self, *, now: datetime | None = None) -> Sequence[JobRecord]:
        current = ensure_utc(now or self._clock())
        with self._lock:
            return self._expire_locked(current)

    def _expire_locked(self, now: datetime) -> Sequence[JobRecord]:
        expired: MutableSequence[JobRecord] = []
        for job in list(self._jobs.values()):
            if not job.is_lease_expired(now):
                continue
            if job.attempt_count >= job.max_attempts:
                update: dict[str, Any] = {
                    "status": JobStatus.FAILED,
                    "last_error": "lease expired after maximum attempts",
                }
            else:
                update = {
                    "status": JobStatus.QUEUED,
                    "available_at": now,
                    "last_error": "worker lease expired; retry scheduled",
                }
            expired.append(
                self._replace(
                    job.model_copy(
                        update={
                            **update,
                            "lease_until": None,
                            "leased_by": None,
                            "updated_at": now,
                        }
                    )
                )
            )
        return expired

    def _get_locked(self, job_id: UUID) -> JobRecord:
        try:
            return self._jobs[job_id]
        except KeyError as error:
            raise JobNotFoundError(f"job {job_id} was not found") from error

    def _replace(self, job: JobRecord) -> JobRecord:
        self._jobs[job.id] = job
        return job

    @staticmethod
    def _assert_lease(job: JobRecord, worker_id: str, now: datetime) -> None:
        if job.status is not JobStatus.RUNNING or job.leased_by != worker_id:
            raise LeaseLostError("worker does not own the active job lease")
        if job.lease_until is None or ensure_utc(job.lease_until) <= now:
            raise LeaseLostError("job lease has expired")


class DBConnection(Protocol):
    def cursor(self) -> Any: ...


class PostgresJobQueue:
    """Postgres-ready queue adapter using a DB-API connection.

    The claim statement uses ``FOR UPDATE SKIP LOCKED`` and all mutations
    include lease ownership predicates.  A connection/pool is injected so
    this module never owns credentials or opens a network connection.
    """

    CLAIM_SQL = """
        UPDATE jobs AS j
        SET status = 'RUNNING', attempt_count = j.attempt_count + 1,
            lease_until = %(lease_until)s, leased_by = %(worker_id)s,
            updated_at = %(now)s
        FROM (
            SELECT id FROM jobs
            WHERE (status = 'QUEUED' AND available_at <= %(now)s)
               OR (status = 'RUNNING' AND lease_until <= %(now)s
                   AND attempt_count < max_attempts)
            ORDER BY priority DESC, available_at ASC, created_at ASC
            FOR UPDATE SKIP LOCKED LIMIT 1
        ) AS ready
        WHERE j.id = ready.id
        RETURNING j.*
    """
    EXPIRE_SQL = """
        UPDATE jobs
        SET status = CASE WHEN attempt_count >= max_attempts THEN 'FAILED' ELSE 'QUEUED' END,
            available_at = CASE WHEN attempt_count >= max_attempts THEN available_at
                ELSE %(available_at)s END,
            lease_until = NULL, leased_by = NULL,
            last_error = CASE WHEN attempt_count >= max_attempts
                THEN 'lease expired after maximum attempts'
                ELSE 'worker lease expired; retry scheduled' END,
            updated_at = %(now)s
        WHERE status = 'RUNNING' AND lease_until <= %(now)s
        RETURNING *
    """

    def __init__(
        self,
        connection: DBConnection,
        *,
        retry_policy: RetryPolicy | None = None,
        clock: Clock = utc_now,
        random_source: RandomSource | None = None,
    ) -> None:
        self.connection = connection
        self.retry_policy = retry_policy or RetryPolicy()
        self._clock = clock
        self._random = random_source or random.random

    def enqueue(
        self,
        job_type: str | EnqueueRequest,
        idempotency_key: str | None = None,
        payload: Mapping[str, Any] | None = None,
        *,
        priority: int = 100,
        max_attempts: int = 5,
        available_at: datetime | None = None,
        research_run_id: UUID | None = None,
    ) -> JobRecord:
        request = _enqueue_request(
            job_type,
            idempotency_key,
            payload,
            priority=priority,
            max_attempts=max_attempts,
            available_at=available_at,
            research_run_id=research_run_id,
        )
        now = ensure_utc(self._clock())
        storage_payload = copy.deepcopy(request.payload)
        if request.research_run_id is not None:
            storage_payload.setdefault("_queue", {})["research_run_id"] = str(
                request.research_run_id
            )
        params = {
            "job_type": request.job_type,
            "idempotency_key": request.idempotency_key,
            "status": JobStatus.QUEUED.value,
            "priority": request.priority,
            "payload": storage_payload,
            "max_attempts": request.max_attempts,
            "available_at": ensure_utc(request.available_at or now),
            "research_run_id": (
                str(request.research_run_id) if request.research_run_id is not None else None
            ),
        }
        row = self._one(
            """
            INSERT INTO jobs (job_type, idempotency_key, status, priority, payload,
                              max_attempts, available_at, research_run_id)
            VALUES (%(job_type)s, %(idempotency_key)s, %(status)s, %(priority)s,
                    %(payload)s, %(max_attempts)s, %(available_at)s, %(research_run_id)s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING *
            """,
            params,
        )
        if row is None:
            existing = self._one(
                "SELECT * FROM jobs WHERE idempotency_key = %(idempotency_key)s",
                {"idempotency_key": request.idempotency_key},
            )
            if existing is None:
                raise JobQueueError("idempotent enqueue could not read existing job")
            record = _row_to_job(existing)
            if _fingerprint(record) != _fingerprint(request):
                raise IdempotencyConflictError(
                    "idempotency key was already used for a different job"
                )
            return record
        return _row_to_job(row)

    def claim(
        self, worker_id: str, *, lease_seconds: float = 60, now: datetime | None = None
    ) -> JobRecord | None:
        worker_id = _required_worker(worker_id)
        current = ensure_utc(now or self._clock())
        row = self._one(
            self.CLAIM_SQL,
            {
                "worker_id": worker_id,
                "lease_until": lease_deadline(current, lease_seconds),
                "now": current,
            },
        )
        return _row_to_job(row) if row is not None else None

    def heartbeat(
        self,
        job: JobRef,
        worker_id: str,
        *,
        lease_seconds: float = 60,
        now: datetime | None = None,
    ) -> JobRecord:
        current = ensure_utc(now or self._clock())
        row = self._one(
            """
            UPDATE jobs SET lease_until = %(lease_until)s, updated_at = %(now)s
            WHERE id = %(id)s AND status = 'RUNNING' AND leased_by = %(worker_id)s
              AND lease_until > %(now)s
            RETURNING *
            """,
            {
                "id": str(_job_id(job)),
                "worker_id": _required_worker(worker_id),
                "lease_until": lease_deadline(current, lease_seconds),
                "now": current,
            },
        )
        if row is None:
            raise LeaseLostError("worker does not own the active job lease")
        return _row_to_job(row)

    def complete(
        self,
        job: JobRef,
        worker_id: str,
        *,
        result: Mapping[str, Any] | None = None,
        provider_request_id: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord:
        current = ensure_utc(now or self._clock())
        metadata: dict[str, Any] = {}
        if result is not None:
            metadata["result"] = copy.deepcopy(dict(result))
        if provider_request_id is not None:
            metadata["provider_request_id"] = provider_request_id
        row = self._one(
            """
            UPDATE jobs SET status = 'SUCCEEDED', lease_until = NULL, leased_by = NULL,
                last_error = NULL,
                payload = CASE WHEN %(metadata)s = '{}'::jsonb THEN payload
                    ELSE payload || jsonb_build_object('_queue', %(metadata)s) END,
                updated_at = %(now)s
            WHERE id = %(id)s AND status = 'RUNNING' AND leased_by = %(worker_id)s
              AND lease_until > %(now)s
            RETURNING *
            """,
            {
                "id": str(_job_id(job)),
                "worker_id": _required_worker(worker_id),
                "metadata": _jsonb_param(metadata),
                "now": current,
            },
        )
        if row is None:
            raise LeaseLostError("worker does not own the active job lease")
        return _row_to_job(row)

    def fail(
        self,
        job: JobRef,
        worker_id: str,
        error: BaseException | str,
        *,
        retryable: bool = True,
        provider_request_id: str | None = None,
        now: datetime | None = None,
    ) -> JobRecord:
        current = ensure_utc(now or self._clock())
        safe_error = sanitize_error(error)
        # Delay is computed outside SQL, but state transition and ownership
        # check remain one atomic UPDATE.
        jitter = self._random() * 2 - 1
        row = self._one(
            """
            UPDATE jobs
            SET status = CASE WHEN %(retryable)s AND attempt_count < max_attempts
                    THEN 'QUEUED' ELSE 'FAILED' END,
                available_at = CASE WHEN %(retryable)s AND attempt_count < max_attempts
                    THEN %(now)s + (
                        LEAST(
                            %(max_delay)s,
                            %(base_delay)s * power(2, greatest(attempt_count - 1, 0))
                        ) * (1 + (%(jitter)s * %(jitter_ratio)s))
                    ) * interval '1 second'
                    ELSE available_at END,
                lease_until = NULL, leased_by = NULL, last_error = %(last_error)s,
                updated_at = %(now)s
            WHERE id = %(id)s AND status = 'RUNNING' AND leased_by = %(worker_id)s
              AND lease_until > %(now)s
            RETURNING *
            """,
            {
                "id": str(_job_id(job)),
                "worker_id": _required_worker(worker_id),
                "retryable": retryable,
                "base_delay": self.retry_policy.base_delay_seconds,
                "max_delay": self.retry_policy.max_delay_seconds,
                "jitter": jitter,
                "jitter_ratio": self.retry_policy.jitter_ratio,
                "last_error": safe_error,
                "now": current,
            },
        )
        if row is None:
            raise LeaseLostError("worker does not own the active job lease")
        return _row_to_job(row)

    def cancel(
        self,
        job: JobRef,
        *,
        worker_id: str | None = None,
        reason: str = "cancelled",
        now: datetime | None = None,
    ) -> JobRecord:
        current = ensure_utc(now or self._clock())
        params: dict[str, Any] = {
            "id": str(_job_id(job)),
            "worker_id": worker_id,
            "reason": sanitize_error(reason),
            "now": current,
        }
        row = self._one(
            """
            UPDATE jobs SET status = 'CANCELLED', lease_until = NULL, leased_by = NULL,
                last_error = %(reason)s, updated_at = %(now)s
            WHERE id = %(id)s AND status IN ('QUEUED', 'RUNNING')
              AND (status = 'QUEUED' OR leased_by = %(worker_id)s)
            RETURNING *
            """,
            params,
        )
        if row is None:
            raise InvalidJobTransitionError("job cannot be cancelled")
        return _row_to_job(row)

    def expire_leases(self, *, now: datetime | None = None) -> Sequence[JobRecord]:
        current = ensure_utc(now or self._clock())
        rows = self._many(self.EXPIRE_SQL, {"now": current, "available_at": current})
        return [_row_to_job(row) for row in rows]

    def _one(self, sql: str, params: Mapping[str, Any]) -> Mapping[str, Any] | None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, dict(params))
            row = cursor.fetchone()
            self._commit()
            return cast(Mapping[str, Any], row) if row is not None else None
        finally:
            close = getattr(cursor, "close", None)
            if callable(close):
                close()

    def _many(self, sql: str, params: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, dict(params))
            rows = cursor.fetchall()
            self._commit()
            return [cast(Mapping[str, Any], row) for row in rows]
        finally:
            close = getattr(cursor, "close", None)
            if callable(close):
                close()

    def _commit(self) -> None:
        commit = getattr(self.connection, "commit", None)
        if callable(commit):
            commit()


SQLJobQueue = PostgresJobQueue
DurableJobQueue = InMemoryJobQueue


_SECRET_PATTERN = re.compile(
    r"(?i)(bearer\s+|(?:api[_-]?key|token|secret|password|authorization|cookie)\s*[:=]\s*)[^\s,;]+"
)
_URL_CREDENTIAL_PATTERN = re.compile(r"(?i)(https?://)([^/@\s]+)@")


def sanitize_error(error: BaseException | str, *, max_length: int = 2000) -> str:
    """Keep a bounded human-readable error while removing credential material."""

    text = str(error).splitlines()[0].strip() if str(error) else "unknown job error"
    text = _URL_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]@", text)
    text = _SECRET_PATTERN.sub(r"\1[REDACTED]", text)
    return text[:max_length]


def _jsonb_param(value: Mapping[str, Any]) -> str:
    """Serialize safe JSON metadata for DB-API drivers without secrets."""

    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _enqueue_request(
    job_type: str | EnqueueRequest,
    idempotency_key: str | None,
    payload: Mapping[str, Any] | None,
    *,
    priority: int,
    max_attempts: int,
    available_at: datetime | None,
    research_run_id: UUID | None,
) -> EnqueueRequest:
    if isinstance(job_type, EnqueueRequest):
        if any(value is not None for value in (idempotency_key, payload)):
            raise ValueError("request object cannot be combined with enqueue fields")
        return job_type
    if idempotency_key is None or not idempotency_key.strip():
        raise ValueError("idempotency_key is required")
    return EnqueueRequest(
        job_type=job_type,
        idempotency_key=idempotency_key,
        payload=dict(payload or {}),
        priority=priority,
        max_attempts=max_attempts,
        available_at=available_at,
        research_run_id=research_run_id,
    )


def _fingerprint(value: EnqueueRequest | JobRecord) -> str:
    payload = value.payload
    return repr(
        (
            value.job_type,
            value.priority,
            value.max_attempts,
            payload,
            getattr(value, "research_run_id", None),
        )
    )


def _job_id(value: JobRef) -> UUID:
    if isinstance(value, JobLease):
        return value.job.id
    if isinstance(value, JobRecord):
        return value.id
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError) as error:
        raise JobNotFoundError(f"invalid job id: {value}") from error


def _required_worker(worker_id: str) -> str:
    normalized = worker_id.strip()
    if not normalized:
        raise ValueError("worker_id is required")
    return normalized


def _row_to_job(row: Mapping[str, Any]) -> JobRecord:
    payload = dict(row)
    if "job_id" in payload and "id" not in payload:
        payload["id"] = payload.pop("job_id")
    payload["status"] = JobStatus(payload.get("status", JobStatus.QUEUED))
    return JobRecord.model_validate(payload)


__all__ = [
    "DBConnection",
    "DurableJobQueue",
    "IdempotencyConflictError",
    "InMemoryJobQueue",
    "InvalidJobTransitionError",
    "JobLease",
    "JobNotFoundError",
    "JobQueue",
    "JobQueueError",
    "LeaseLostError",
    "PostgresJobQueue",
    "SQLJobQueue",
    "sanitize_error",
]
