"""Shared fixture loading for the Phase 01-01 red-test contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _load_json(name: str) -> Any:
    with (FIXTURE_ROOT / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


@pytest.fixture
def auth_users() -> dict[str, dict[str, str]]:
    return _load_json("auth_users.json")


@pytest.fixture
def valid_settings_values() -> dict[str, Any]:
    return _load_json("config_valid.json")


@pytest.fixture
def valid_settings(valid_settings_values: dict[str, Any]):
    from app.config.settings import Settings

    return Settings(**valid_settings_values)


@pytest.fixture
def app(valid_settings):
    from app.main import create_app

    return create_app(settings=valid_settings)


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
