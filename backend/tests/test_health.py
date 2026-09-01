"""HTTP health contracts for the backend application boundary."""

from __future__ import annotations

from typing import Any


def _assert_stable_health_response(response: Any) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok"}


def test_health_returns_static_ok_payload(client) -> None:
    _assert_stable_health_response(client.get("/health"))


def test_versioned_health_matches_unversioned_health(client) -> None:
    health_response = client.get("/health")
    versioned_response = client.get("/v1/health")

    _assert_stable_health_response(health_response)
    _assert_stable_health_response(versioned_response)
    assert versioned_response.json() == health_response.json()
