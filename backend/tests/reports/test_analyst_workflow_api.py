"""Owner-scoped contracts for analyst workflow extensions."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .test_report_workspace_api import OWNER_REPORT_ID, REQUEST_ID, _assert_stable_error


def test_research_mode_persists_without_changing_report_status(
    owner_report_client: TestClient,
) -> None:
    response = owner_report_client.post(
        "/v1/reports",
        json={
            "title": "NVIDIA - Earnings Review",
            "subject": {"query": "NVIDIA", "country_code": "US", "ticker": "NVDA"},
            "focus": ["guidance", "cash-flow"],
            "depth": "STANDARD",
            "research_mode": "EARNINGS",
        },
        headers={"X-Request-ID": REQUEST_ID, "Idempotency-Key": "nvidia-earnings-001"},
    )

    assert response.status_code == 201
    created = response.json()
    assert created["research_mode"] == "EARNINGS"
    assert created["status"] == "DRAFT"

    detail = owner_report_client.get(
        f"/v1/reports/{created['report_id']}",
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert detail.status_code == 200
    assert detail.json()["research_mode"] == "EARNINGS"


def test_thesis_tracker_is_owner_scoped_and_separate_from_claim_verdicts(
    owner_report_client: TestClient,
) -> None:
    created = owner_report_client.post(
        f"/v1/reports/{OWNER_REPORT_ID}/thesis",
        json={
            "statement": "Demand remains material through the next reported period.",
            "falsifier": "Independent channel evidence indicates a sustained demand reversal.",
            "materiality": "HIGH",
        },
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert created.status_code == 201
    thesis = created.json()
    assert thesis["status"] == "OPEN"
    assert "verdict" not in thesis

    updated = owner_report_client.patch(
        f"/v1/reports/{OWNER_REPORT_ID}/thesis/{thesis['thesis_point_id']}",
        json={"status": "WEAKENED", "review_note": "Cash conversion needs a period-aligned check."},
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "WEAKENED"
    assert updated.json()["review_note"] == "Cash conversion needs a period-aligned check."

def test_other_user_cannot_read_another_reports_thesis_points(
    other_user_report_client: TestClient,
) -> None:
    unauthorized = other_user_report_client.get(
        f"/v1/reports/{OWNER_REPORT_ID}/thesis",
        headers={"X-Request-ID": REQUEST_ID},
    )
    _assert_stable_error(unauthorized, status_code=403, code="FORBIDDEN")


def test_change_brief_and_tearsheet_keep_citations_and_fixture_limitations(
    owner_report_client: TestClient,
) -> None:
    brief = owner_report_client.get(
        f"/v1/reports/{OWNER_REPORT_ID}/change-brief",
        params={"kind": "FILING"},
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert brief.status_code == 200
    body = brief.json()
    assert body["kind"] == "FILING"
    assert body["items"]
    assert all(item["citations"] for item in body["items"])
    assert any("Fixture" in limitation for limitation in body["limitations"])

    tearsheet = owner_report_client.get(
        f"/v1/reports/{OWNER_REPORT_ID}/tearsheet",
        headers={"X-Request-ID": REQUEST_ID},
    )
    assert tearsheet.status_code == 200
    sheet = tearsheet.json()
    assert sheet["research_mode"] == "INITIATION"
    assert all(section["citations"] for section in sheet["sections"])
    assert any("Fixture" in limitation for limitation in sheet["limitations"])


def test_analyst_workflow_validation_errors_are_stable(
    owner_report_client: TestClient,
) -> None:
    invalid = owner_report_client.get(
        f"/v1/reports/{OWNER_REPORT_ID}/change-brief",
        params={"kind": "NOT_A_BRIEF"},
        headers={"X-Request-ID": REQUEST_ID},
    )
    _assert_stable_error(invalid, status_code=422, code="VALIDATION_ERROR")


def test_analyst_workflow_endpoints_require_authentication(client: TestClient) -> None:
    unauthenticated = client.get(
        f"/v1/reports/{OWNER_REPORT_ID}/tearsheet",
        headers={"X-Request-ID": REQUEST_ID},
    )
    _assert_stable_error(unauthenticated, status_code=401, code="UNAUTHENTICATED")
