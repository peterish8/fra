"""Fixture-only report repository and authenticated clients for red contracts."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security.auth import AuthenticatedUser, get_current_user

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "report_workspace_cases.json"


class FixtureReportRepository:
    """In-memory report/evidence state; it must never call Supabase or a provider."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.reports = [dict(report) for report in payload["reports"]]
        self.shared_evidence = [dict(item) for item in payload["shared_evidence"]]

    def owner_report_ids(self, owner_user_id: str) -> set[str]:
        return {
            report["report_id"]
            for report in self.reports
            if report["owner_user_id"] == owner_user_id and report["deleted_at"] is None
        }

    def shared_evidence_count(self) -> int:
        return len(self.shared_evidence)


@pytest.fixture
def report_repository() -> FixtureReportRepository:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return FixtureReportRepository(json.load(fixture_file))


def _authenticated_client(
    report_app: FastAPI,
    user: dict[str, str],
) -> Iterator[TestClient]:
    identity = AuthenticatedUser(id=user["id"], email=user["email"], role=user["role"])

    def fixture_identity() -> AuthenticatedUser:
        return identity

    report_app.dependency_overrides[get_current_user] = fixture_identity
    try:
        with TestClient(report_app) as test_client:
            yield test_client
    finally:
        report_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def report_app(app: FastAPI, report_repository: FixtureReportRepository) -> FastAPI:
    app.state.report_repository = report_repository
    return app


@pytest.fixture
def owner_report_client(
    report_app: FastAPI,
    auth_users: dict[str, dict[str, str]],
) -> Iterator[TestClient]:
    yield from _authenticated_client(report_app, auth_users["owner"])


@pytest.fixture
def other_user_report_client(
    report_app: FastAPI,
    auth_users: dict[str, dict[str, str]],
) -> Iterator[TestClient]:
    yield from _authenticated_client(report_app, auth_users["other"])
