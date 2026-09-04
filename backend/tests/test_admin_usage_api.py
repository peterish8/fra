"""Admin usage overview contracts with fixture identities only."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.security.auth import AuthenticatedUser, get_current_user


def _identity(*, role: str) -> AuthenticatedUser:
    return AuthenticatedUser(
        id="33333333-3333-4333-8333-333333333333",
        email="admin@example.test",
        role=role,
    )


def test_admin_usage_overview_rejects_authenticated_non_admin(app: Any) -> None:
    app.dependency_overrides[get_current_user] = lambda: _identity(role="authenticated")
    try:
        with TestClient(app) as client:
            response = client.get("/v1/admin/usage-overview")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ADMIN_REQUIRED"


def test_admin_usage_overview_returns_labelled_fixture_for_admin(app: Any) -> None:
    app.dependency_overrides[get_current_user] = lambda: _identity(role="admin")
    try:
        with TestClient(app) as client:
            response = client.get("/v1/admin/usage-overview")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "FIXTURE"
    assert body["observation_window_hours"] == 24
    assert body["registered_users"] == 3
    assert body["research_runs_in_window"] == 22
    assert {item["quota_status"] for item in body["users"]} == {
        "AVAILABLE",
        "NEARING_LIMIT",
        "AT_LIMIT",
    }
