"""Typed configuration and secret-safe observability contracts."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from pydantic import ValidationError


def test_missing_required_settings_fail_without_echoing_secret_values(
    valid_settings_values: dict[str, Any],
) -> None:
    from app.config.settings import Settings

    missing_values = dict(valid_settings_values)
    missing_values.pop("supabase_url")

    with pytest.raises((ValidationError, ValueError)) as caught:
        Settings(**missing_values)

    message = str(caught.value)
    assert "supabase_url" in message.lower() or "SUPABASE_URL" in message
    for secret_value in (
        valid_settings_values["supabase_service_role_key"],
        valid_settings_values["perplexity_api_key"],
        valid_settings_values["database_url"],
    ):
        assert secret_value not in message


def test_valid_settings_load_typed_values_without_network(
    valid_settings,
    valid_settings_values: dict[str, Any],
) -> None:
    assert valid_settings.app_env == valid_settings_values["app_env"]
    assert str(valid_settings.app_base_url) == valid_settings_values["app_base_url"]
    assert str(valid_settings.api_base_url) == valid_settings_values["api_base_url"]
    assert valid_settings.supabase_url == valid_settings_values["supabase_url"]
    assert valid_settings.max_follow_up_loops == 3


def test_request_id_and_secret_redaction_are_present_in_response_and_logs(
    client,
    caplog: pytest.LogCaptureFixture,
    valid_settings_values: dict[str, Any],
) -> None:
    caplog.set_level(logging.INFO)
    request_id = "req_fixture_redaction_001"
    secrets = (
        "fixture-bearer-token",
        "fixture-cookie-value",
        "fixture-api-key",
        valid_settings_values["supabase_service_role_key"],
        valid_settings_values["perplexity_api_key"],
    )

    response = client.get(
        "/health",
        headers={
            "X-Request-ID": request_id,
            "Authorization": f"Bearer {secrets[0]}",
            "Cookie": f"session={secrets[1]}",
            "X-Api-Key": secrets[2],
        },
    )

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == request_id

    log_text = caplog.text
    assert request_id in log_text
    assert "status" in log_text.lower()
    assert "duration_ms" in log_text.lower()
    for secret in secrets:
        assert secret not in log_text
