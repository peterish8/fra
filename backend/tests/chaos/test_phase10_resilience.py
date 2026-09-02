"""Chaos contracts: provider failures and worker races must be recoverable."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.jobs.queue import InMemoryJobQueue, JobStatus, LeaseLostError

NOW = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


def test_provider_timeout_is_retryable_and_not_silently_published() -> None:
    queue = InMemoryJobQueue(clock=lambda: NOW, random_source=lambda: 0.5)
    queued = queue.enqueue("RESEARCH", idempotency_key="timeout-001", payload={"stage": "retrieve"})
    claimed = queue.claim("worker-a", now=NOW, lease_seconds=30)
    assert claimed is not None
    retried = queue.fail(queued, "worker-a", "TIMEOUT", retryable=True, now=NOW)
    assert retried.status == "QUEUED"
    assert retried.last_error == "TIMEOUT"
    assert not queue.list(status=JobStatus.SUCCEEDED)


@pytest.mark.parametrize("provider_status", ["RATE_LIMITED", "TIMEOUT", "TEMPORARY_FAILURE"])
def test_provider_degradation_is_explicit_and_never_becomes_evidence(
    provider_status: str,
) -> None:
    from app.providers.contracts import normalize_provider_result

    result = normalize_provider_result(
        provider="fixture-provider",
        operation="search",
        payload=None,
        provider_status=provider_status,
        provider_request_id="provider-request-001",
        retrieved_at=NOW,
        latency_ms=100,
        cost_usd_estimate=0,
        raw_metadata={"retry_after": "30"},
        error_code=provider_status,
        retry_classification="RETRYABLE",
    )
    assert result.status.value == provider_status
    assert result.data is None
    assert result.retry_classification == "RETRYABLE"


def test_worker_crash_and_lease_expiry_requeues_once_for_next_worker() -> None:
    queue = InMemoryJobQueue(clock=lambda: NOW, random_source=lambda: 0.5)
    job = queue.enqueue("RESEARCH", idempotency_key="crash-001", payload={})
    first = queue.claim("worker-a", now=NOW, lease_seconds=10)
    assert first is not None
    expired = queue.expire_leases(now=NOW + timedelta(seconds=11))
    assert len(expired) == 1
    second = queue.claim("worker-b", now=NOW + timedelta(seconds=11), lease_seconds=10)
    assert second is not None
    assert second.id == job.id
    assert second.attempt_count == 2
    with pytest.raises(LeaseLostError):
        queue.complete(job, "worker-a", now=NOW + timedelta(seconds=11))


def test_duplicate_cron_trigger_replays_one_job_and_conflicting_payload_is_rejected() -> None:
    from app.jobs.queue import IdempotencyConflictError

    queue = InMemoryJobQueue()
    first = queue.enqueue(
        "WATCHLIST_REFRESH",
        idempotency_key="cron:2026-09-02",
        payload={"window": "weekly"},
    )
    replay = queue.enqueue(
        "WATCHLIST_REFRESH",
        idempotency_key="cron:2026-09-02",
        payload={"window": "weekly"},
    )
    assert replay.id == first.id
    assert len(queue.jobs) == 1
    with pytest.raises(IdempotencyConflictError):
        queue.enqueue(
            "WATCHLIST_REFRESH",
            idempotency_key="cron:2026-09-02",
            payload={"window": "daily"},
        )


def test_budget_exhaustion_preserves_partial_run_without_creating_a_second_version() -> None:
    from uuid import UUID

    from app.domain.research.models import ResearchBudget, RunStage
    from app.domain.research.service import ResearchRunService

    service = ResearchRunService()
    run = service.create_run(
        report_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        owner_user_id="owner-1",
        idempotency_key="chaos-budget-001",
        budget=ResearchBudget(max_cost_usd=1),
    )
    service.start(run.run_id, stage=RunStage.PLANNING)
    decision = service.consume_budget(run.run_id, cost_usd=2)
    assert decision.allowed is False
    assert service.get_run(run.run_id).status == "PARTIAL"
    assert service.ensure_report_version(
        run.run_id, lambda: "11111111-1111-4111-8111-111111111111"
    )
    assert service.ensure_report_version(
        run.run_id, lambda: "22222222-2222-4222-8222-222222222222"
    ) == UUID("11111111-1111-4111-8111-111111111111")
