"""Report-scoped source-lineage API contracts."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.sources import ReportSourcePage, ReportSourceSummary, SourceSnapshotSummary
from app.domain.reports.repository import InMemoryReportRepository
from app.security.auth import AuthenticatedUser, get_current_user

OWNER_ID = "11111111-1111-4111-8111-111111111111"
OTHER_ID = "22222222-2222-4222-8222-222222222222"
OWNER_REPORT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
MISSING_REPORT_ID = "99999999-9999-4999-8999-999999999999"
REQUEST_ID = "req_source_api_fixture_001"
REPORT_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "report_workspace_cases.json"


class _FixtureSourceRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def list_report_sources(
        self,
        *,
        report_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> ReportSourcePage:
        self.calls.append({"report_id": report_id, "cursor": cursor, "limit": limit})
        return ReportSourcePage(
            items=[
                ReportSourceSummary(
                    source_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaab"),
                    identity_key="url:https://acme.example.test/report",
                    canonical_url="https://acme.example.test/report",
                    publisher="Fixture Publisher",
                    domain="acme.example.test",
                    source_type="NEWS",
                    authority_tier="C1",
                    ownership_relation="INDEPENDENT",
                    source_family_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaac"),
                    source_family_reason="Independent source family",
                    latest_snapshot=SourceSnapshotSummary(
                        snapshot_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaad"),
                        retrieved_at="2026-09-01T09:00:00Z",
                        published_at="2026-08-31T09:00:00Z",
                        content_hash="b" * 64,
                        retention_mode="METADATA_ONLY",
                        provider_request_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaae"),
                    ),
                )
            ],
            next_cursor=None,
        )


def _report_repository() -> InMemoryReportRepository:
    with REPORT_FIXTURE.open(encoding="utf-8") as fixture_file:
        payload = json.load(fixture_file)
    return InMemoryReportRepository(payload["reports"])


@contextmanager
def _authenticated_client(
    application: FastAPI,
    user_id: str,
) -> Iterator[TestClient]:
    identity = AuthenticatedUser(
        id=user_id,
        email=f"{user_id}@fixture.test",
        role="authenticated",
    )

    def fixture_identity() -> AuthenticatedUser:
        return identity

    application.dependency_overrides[get_current_user] = fixture_identity
    try:
        with TestClient(application) as test_client:
            yield test_client
    finally:
        application.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def source_app(app: FastAPI) -> FastAPI:
    app.state.report_repository = _report_repository()
    return app


@pytest.fixture
def owner_source_client(source_app: FastAPI) -> Iterator[TestClient]:
    source_app.state.report_source_repository = _FixtureSourceRepository()
    with _authenticated_client(source_app, OWNER_ID) as client:
        yield client


@pytest.fixture
def other_source_client(source_app: FastAPI) -> Iterator[TestClient]:
    source_app.state.report_source_repository = _FixtureSourceRepository()
    with _authenticated_client(source_app, OTHER_ID) as client:
        yield client


def _assert_error(response: Any, *, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert body["error"]["request_id"] == REQUEST_ID


def test_unauthenticated_source_listing_is_rejected(client: TestClient) -> None:
    response = client.get(
        f"/v1/reports/{OWNER_REPORT_ID}/sources",
        headers={"X-Request-ID": REQUEST_ID},
    )

    _assert_error(response, status_code=401, code="UNAUTHENTICATED")


def test_missing_source_repository_is_a_stable_service_unavailable(
    source_app: FastAPI,
) -> None:
    with _authenticated_client(source_app, OWNER_ID) as client:
        response = client.get(
            f"/v1/reports/{OWNER_REPORT_ID}/sources",
            headers={"X-Request-ID": REQUEST_ID},
        )

    _assert_error(response, status_code=503, code="SOURCE_STORE_UNAVAILABLE")


def test_missing_report_is_not_disclosed_to_source_repository(
    owner_source_client: TestClient,
) -> None:
    response = owner_source_client.get(
        f"/v1/reports/{MISSING_REPORT_ID}/sources",
        headers={"X-Request-ID": REQUEST_ID},
    )

    _assert_error(response, status_code=404, code="NOT_FOUND")


def test_wrong_report_owner_is_forbidden_before_source_lookup(
    other_source_client: TestClient,
) -> None:
    response = other_source_client.get(
        f"/v1/reports/{OWNER_REPORT_ID}/sources",
        headers={"X-Request-ID": REQUEST_ID},
    )

    _assert_error(response, status_code=403, code="FORBIDDEN")


def test_authorized_source_listing_returns_retention_safe_lineage_summary(
    owner_source_client: TestClient,
) -> None:
    response = owner_source_client.get(
        f"/v1/reports/{OWNER_REPORT_ID}/sources",
        params={"limit": 20},
        headers={"X-Request-ID": REQUEST_ID},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "next_cursor"}
    item = body["items"][0]
    assert item["identity_key"] == "url:https://acme.example.test/report"
    assert item["ownership_relation"] == "INDEPENDENT"
    assert item["latest_snapshot"]["retention_mode"] == "METADATA_ONLY"
    assert item["latest_snapshot"]["content_hash"] == "b" * 64
    for forbidden in ("content", "text", "body", "extracted_text", "full_content", "storage_ref"):
        assert forbidden not in item
        assert forbidden not in item["latest_snapshot"]
