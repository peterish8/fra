"""Phase 02 Plan 01 red contracts for report workspace CRUD and library behavior."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from .conftest import FixtureReportRepository

REQUEST_ID = "req_report_fixture_001"
OWNER_REPORT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_REPORT_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


def _assert_stable_error(response: Any, *, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) >= {"code", "message", "request_id"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert body["error"]["request_id"] == REQUEST_ID
    assert response.headers["X-Request-ID"] == REQUEST_ID


def test_authenticated_create_persists_workspace_fields_and_returns_stable_identifier(
    owner_report_client: TestClient,
    report_repository: FixtureReportRepository,
) -> None:
    payload = {
        "title": "Apple - Financial Health",
        "subject": {
            "query": "Apple",
            "country_code": "US",
            "ticker": "AAPL",
            "domain": "apple.com",
        },
        "focus": ["financials", "disclosure"],
        "depth": "STANDARD",
    }

    response = owner_report_client.post(
        "/v1/reports",
        json=payload,
        headers={"X-Request-ID": REQUEST_ID, "Idempotency-Key": "create-apple-001"},
    )

    assert response.status_code == 201
    created = response.json()
    UUID(created["report_id"])
    assert created["status"] == "DRAFT"

    detail = owner_report_client.get(
        f"/v1/reports/{created['report_id']}",
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert detail.status_code == 200
    assert detail.json()["title"] == payload["title"]
    assert detail.json()["subject"] == payload["subject"]
    assert detail.json()["focus"] == payload["focus"]
    assert detail.json()["depth"] == payload["depth"]
    assert report_repository.owner_report_ids("11111111-1111-4111-8111-111111111111")


def test_library_search_filter_and_open_are_owner_scoped(
    owner_report_client: TestClient,
) -> None:
    response = owner_report_client.get(
        "/v1/reports",
        params={"q": "nvidia", "status": "DRAFT", "limit": 20},
        headers={"X-Request-ID": REQUEST_ID},
    )

    assert response.status_code == 200
    page = response.json()
    assert set(page) == {"items", "next_cursor"}
    assert [item["report_id"] for item in page["items"]] == [OWNER_REPORT_ID]
    assert page["items"][0]["status"] == "DRAFT"

    opened = owner_report_client.get(
        f"/v1/reports/{OWNER_REPORT_ID}",
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert opened.status_code == 200
    assert opened.json()["report_id"] == OWNER_REPORT_ID


def test_library_cursor_pagination_and_empty_result_are_explicit(
    owner_report_client: TestClient,
) -> None:
    first_page = owner_report_client.get(
        "/v1/reports",
        params={"limit": 1},
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert first_page.status_code == 200
    assert len(first_page.json()["items"]) == 1
    assert first_page.json()["next_cursor"]

    empty = owner_report_client.get(
        "/v1/reports",
        params={"q": "does-not-exist", "limit": 20},
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "next_cursor": None}


def test_wrong_owner_cannot_open_or_delete_report_uuid(
    other_user_report_client: TestClient,
) -> None:
    opened = other_user_report_client.get(
        f"/v1/reports/{OWNER_REPORT_ID}",
        headers={"X-Request-ID": REQUEST_ID},
    )
    _assert_stable_error(opened, status_code=403, code="FORBIDDEN")

    deleted = other_user_report_client.delete(
        f"/v1/reports/{OWNER_REPORT_ID}",
        headers={"X-Request-ID": REQUEST_ID},
    )
    _assert_stable_error(deleted, status_code=403, code="FORBIDDEN")


def test_soft_delete_hides_workspace_but_preserves_shared_evidence(
    owner_report_client: TestClient,
    report_repository: FixtureReportRepository,
) -> None:
    evidence_before = report_repository.shared_evidence_count()

    response = owner_report_client.delete(
        f"/v1/reports/{OWNER_REPORT_ID}",
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert response.status_code == 204
    assert response.content == b""
    assert report_repository.shared_evidence_count() == evidence_before

    library = owner_report_client.get(
        "/v1/reports",
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert library.status_code == 200
    assert OWNER_REPORT_ID not in {item["report_id"] for item in library.json()["items"]}

    reopened = owner_report_client.get(
        f"/v1/reports/{OWNER_REPORT_ID}",
        headers={"X-Request-ID": REQUEST_ID},
    )
    _assert_stable_error(reopened, status_code=404, code="NOT_FOUND")


def test_create_is_idempotent_for_same_user_action_and_key(
    owner_report_client: TestClient,
) -> None:
    payload = {
        "title": "Microsoft - Standard Research",
        "subject": {"query": "Microsoft", "country_code": "US", "ticker": "MSFT"},
        "focus": ["growth"],
        "depth": "STANDARD",
    }
    headers = {"X-Request-ID": REQUEST_ID, "Idempotency-Key": "create-msft-001"}

    first = owner_report_client.post("/v1/reports", json=payload, headers=headers)
    repeat = owner_report_client.post("/v1/reports", json=payload, headers=headers)

    assert first.status_code == 201
    assert repeat.status_code == 201
    assert repeat.json() == first.json()


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "expected_status", "expected_code"),
    [
        ("get", "/v1/reports/not-a-uuid", {}, 422, "VALIDATION_ERROR"),
        ("get", "/v1/reports/ffffffff-ffff-4fff-8fff-ffffffffffff", {}, 404, "NOT_FOUND"),
        (
            "post",
            "/v1/reports",
            {"json": {"title": "", "subject": {"query": "A"}, "depth": "ULTRA"}},
            422,
            "VALIDATION_ERROR",
        ),
    ],
)
def test_report_errors_use_stable_envelope(
    owner_report_client: TestClient,
    method: str,
    path: str,
    kwargs: dict[str, Any],
    expected_status: int,
    expected_code: str,
) -> None:
    response = getattr(owner_report_client, method)(
        path,
        headers={"X-Request-ID": REQUEST_ID},
        **kwargs,
    )
    _assert_stable_error(response, status_code=expected_status, code=expected_code)


def test_report_endpoints_require_authentication(client: TestClient) -> None:
    response = client.get("/v1/reports", headers={"X-Request-ID": REQUEST_ID})
    _assert_stable_error(response, status_code=401, code="UNAUTHENTICATED")
