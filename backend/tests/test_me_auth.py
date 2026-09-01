"""Authenticated identity endpoint contracts using fixture identities only."""

from __future__ import annotations


def _assert_api_error(response, *, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert body["error"]["request_id"]


def test_me_without_credentials_is_stably_unauthenticated(client) -> None:
    response = client.get("/v1/me")

    _assert_api_error(response, status_code=401, code="UNAUTHENTICATED")


def test_me_with_malformed_bearer_token_is_stably_unauthenticated(
    client,
) -> None:
    response = client.get(
        "/v1/me",
        headers={"Authorization": "Bearer fixture-not-a-jwt"},
    )

    _assert_api_error(response, status_code=401, code="UNAUTHENTICATED")
    assert "fixture-not-a-jwt" not in response.text


def test_me_returns_fixture_identity_without_calling_supabase(
    app,
    auth_users,
) -> None:
    from fastapi.testclient import TestClient

    from app.security.auth import AuthenticatedUser, get_current_user

    user = auth_users["owner"]
    identity = AuthenticatedUser(
        id=user["id"],
        email=user["email"],
        role=user["role"],
    )

    def fixture_identity() -> AuthenticatedUser:
        return identity

    app.dependency_overrides[get_current_user] = fixture_identity
    try:
        with TestClient(app) as client:
            response = client.get("/v1/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {"id": user["id"], "email": user["email"]}
