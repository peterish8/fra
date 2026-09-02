from app.observability.diagnostics import safe_diagnostics


def test_diagnostics_redact_secrets_and_prompts() -> None:
    output = safe_diagnostics(
        {"run_id": "r1", "api_key": "secret", "prompt": "ignore gates", "stage": "VERIFY"}
    )
    assert output["api_key"] == "[REDACTED]"
    assert output["prompt"] == "[REDACTED]"
    assert output["run_id"] == "r1"
