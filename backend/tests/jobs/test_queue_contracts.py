"""Concurrency, lease, retry, cancellation, and idempotency contracts."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from app.jobs.queue import InMemoryJobQueue

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "job_cases.json"
NOW = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def _queue() -> InMemoryJobQueue:
    # Keep retry jitter deterministic while exercising the production policy.
    # Pin the queue clock too: the scenarios use a fixed ``NOW`` and must not
    # become unavailable merely because wall-clock time moved past the fixture.
    return InMemoryJobQueue(clock=lambda: NOW, random_source=lambda: 0.5)


def test_concurrent_workers_can_claim_a_ready_job_only_once() -> None:
    queue = _queue()
    queued = queue.enqueue(
        job_type="RESEARCH",
        payload={"report_id": "report-1"},
        idempotency_key="research-1",
    )
    barrier = threading.Barrier(2)
    claimed: list[Any] = []

    def claim(worker_id: str) -> None:
        barrier.wait()
        claimed.append(queue.claim(worker_id=worker_id, now=NOW, lease_seconds=60))

    workers = [threading.Thread(target=claim, args=(f"worker-{index}",)) for index in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=2)

    winners = [job for job in claimed if job is not None]
    assert len(winners) == 1
    assert _field(winners[0], "job_id") == _field(queued, "job_id")
    assert _field(winners[0], "status") == "RUNNING"
    assert _field(winners[0], "attempt_count") == 1


def test_expired_lease_is_reclaimable_after_worker_crash() -> None:
    queue = _queue()
    queued = queue.enqueue(job_type="RESEARCH", payload={}, idempotency_key="crash-1")
    first = queue.claim(worker_id="worker-a", now=NOW, lease_seconds=30)
    assert first is not None

    with pytest.raises((PermissionError, ValueError, RuntimeError)):
        queue.complete(
            _field(queued, "job_id"),
            worker_id="worker-a",
            now=NOW + timedelta(seconds=31),
        )

    reclaimed = queue.claim(worker_id="worker-b", now=NOW + timedelta(seconds=31), lease_seconds=30)
    assert reclaimed is not None
    assert _field(reclaimed, "job_id") == _field(queued, "job_id")
    assert _field(reclaimed, "attempt_count") == 2


def test_heartbeat_extends_lease_for_the_current_worker() -> None:
    queue = _queue()
    queued = queue.enqueue(job_type="RESEARCH", payload={}, idempotency_key="heartbeat-1")
    claim = queue.claim(worker_id="worker-a", now=NOW, lease_seconds=30)
    assert claim is not None
    renewed = queue.heartbeat(
        _field(queued, "job_id"),
        worker_id="worker-a",
        now=NOW + timedelta(seconds=20),
        lease_seconds=60,
    )
    assert _field(renewed, "lease_until") == NOW + timedelta(seconds=80)
    assert (
        queue.claim(worker_id="worker-b", now=NOW + timedelta(seconds=31), lease_seconds=30) is None
    )


def test_retryable_error_requeues_but_permanent_error_fails() -> None:
    queue = _queue()
    retryable = queue.enqueue(job_type="RESEARCH", payload={}, idempotency_key="retry-1")
    claimed = queue.claim(worker_id="worker-a", now=NOW, lease_seconds=30)
    assert claimed is not None
    result = queue.fail(
        _field(retryable, "job_id"),
        worker_id="worker-a",
        error=_cases()["queue_cases"]["retryable_error"]["error_code"],
        retryable=True,
        now=NOW,
    )
    assert _field(result, "status") == "QUEUED"
    assert _field(result, "available_at") > NOW

    permanent = queue.enqueue(job_type="RESEARCH", payload={}, idempotency_key="permanent-1")
    queue.claim(worker_id="worker-a", now=NOW, lease_seconds=30)
    failed = queue.fail(
        _field(permanent, "job_id"),
        worker_id="worker-a",
        error=_cases()["queue_cases"]["permanent_error"]["error_code"],
        retryable=False,
        now=NOW,
    )
    assert _field(failed, "status") == "FAILED"


def test_cancelled_job_cannot_be_claimed_or_completed() -> None:
    queue = _queue()
    queued = queue.enqueue(job_type="RESEARCH", payload={}, idempotency_key="cancel-queued")
    cancelled = queue.cancel(_field(queued, "job_id"), reason="user_requested")
    assert _field(cancelled, "status") == "CANCELLED"
    assert queue.claim(worker_id="worker-a", now=NOW, lease_seconds=30) is None

    running = queue.enqueue(job_type="RESEARCH", payload={}, idempotency_key="cancel-running")
    claim = queue.claim(worker_id="worker-a", now=NOW, lease_seconds=30)
    assert claim is not None
    cancelled = queue.cancel(
        _field(running, "job_id"), worker_id="worker-a", reason="user_requested"
    )
    assert _field(cancelled, "status") == "CANCELLED"
    with pytest.raises((PermissionError, ValueError, RuntimeError)):
        queue.complete(_field(running, "job_id"), worker_id="worker-a", now=NOW)


def test_priority_claims_urgent_jobs_first() -> None:
    queue = _queue()
    for case in _cases()["queue_cases"]["priority_order"]:
        queue.enqueue(
            job_type="RESEARCH",
            payload={},
            idempotency_key=case["idempotency_key"],
            priority=case["priority"],
        )
    claimed_keys: list[str] = []
    for index in range(3):
        job = queue.claim(worker_id=f"worker-{index}", now=NOW, lease_seconds=30)
        assert job is not None
        claimed_keys.append(_field(job, "idempotency_key"))
        queue.complete(_field(job, "job_id"), worker_id=f"worker-{index}", now=NOW)
    assert claimed_keys == ["urgent", "high", "low"]


def test_max_attempts_stops_retry_loop() -> None:
    queue = _queue()
    queued = queue.enqueue(
        job_type="RESEARCH",
        payload={},
        idempotency_key="max-attempts-1",
        max_attempts=_cases()["queue_cases"]["max_attempts"],
    )
    job_id = _field(queued, "job_id")
    for attempt in range(2):
        claimed = queue.claim(
            worker_id=f"worker-{attempt}",
            now=NOW + timedelta(hours=attempt + 1),
            lease_seconds=30,
        )
        assert claimed is not None
        result = queue.fail(
            job_id,
            worker_id=f"worker-{attempt}",
            error="TEMPORARY_FAILURE",
            retryable=True,
            now=NOW + timedelta(hours=attempt + 1),
        )
    assert _field(result, "status") == "FAILED"
    assert _field(result, "attempt_count") == 2
    assert (
        queue.claim(worker_id="worker-final", now=NOW + timedelta(days=1), lease_seconds=30) is None
    )


def test_duplicate_enqueue_replays_original_job_without_new_record() -> None:
    queue = _queue()
    first = queue.enqueue(
        job_type="RESEARCH",
        payload={"report_id": "report-1"},
        idempotency_key="same-request",
    )
    replay = queue.enqueue(
        job_type="RESEARCH",
        payload={"report_id": "report-1"},
        idempotency_key="same-request",
    )
    assert _field(replay, "job_id") == _field(first, "job_id")
    with pytest.raises((ValueError, RuntimeError)):
        queue.enqueue(
            job_type="RESEARCH",
            payload={"report_id": "different"},
            idempotency_key="same-request",
        )
