"""Reusable server-side owner authorization contracts."""

from __future__ import annotations

import pytest


def _assert_owner_error(caught: pytest.ExceptionInfo[Exception], *, status_code: int, code: str) -> None:
    error = caught.value
    assert getattr(error, "status_code") == status_code
    detail = getattr(error, "detail")
    assert detail["error"]["code"] == code
    assert detail["error"]["request_id"] == "req_owner_fixture_001"


def test_owner_authorization_allows_matching_user(auth_users) -> None:
    from app.api.dependencies import assert_owner

    user = auth_users["owner"]
    assert_owner(
        current_user_id=user["id"],
        resource_owner_id=user["id"],
        request_id="req_owner_fixture_001",
    )


def test_owner_authorization_rejects_missing_identity_as_unauthenticated(
    auth_users,
) -> None:
    from app.api.dependencies import assert_owner

    with pytest.raises(Exception) as caught:
        assert_owner(
            current_user_id=None,
            resource_owner_id=auth_users["owner"]["id"],
            request_id="req_owner_fixture_001",
        )

    _assert_owner_error(caught, status_code=401, code="UNAUTHENTICATED")


def test_owner_authorization_rejects_wrong_owner_as_forbidden(auth_users) -> None:
    from app.api.dependencies import assert_owner

    with pytest.raises(Exception) as caught:
        assert_owner(
            current_user_id=auth_users["other"]["id"],
            resource_owner_id=auth_users["owner"]["id"],
            request_id="req_owner_fixture_001",
        )

    _assert_owner_error(caught, status_code=403, code="FORBIDDEN")
