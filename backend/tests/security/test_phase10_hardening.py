"""Blocking security regression contracts for the release gate."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError


def test_auth_boundary_rejects_missing_and_invalid_bearer_tokens(client: object) -> None:
    response = client.get("/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    response = client.get("/v1/me", headers={"Authorization": "Basic not-a-bearer"})
    assert response.status_code == 401


def test_url_policy_revalidates_redirects_and_rejects_private_targets() -> None:
    from app.security.url_policy import validate_redirect_chain, validate_url

    metadata = validate_url(
        "http://169.254.169.254/latest/meta-data",
        resolver=lambda _: ["169.254.169.254"],
    )
    assert not metadata.allowed
    result = validate_redirect_chain(
        "https://public.example.test/start",
        ["http://127.0.0.1/admin"],
        resolver=lambda host: ["93.184.216.34"] if host == "public.example.test" else ["127.0.0.1"],
    )
    assert result.allowed is False
    assert "PRIVATE" in str(result.reason) or "LOOPBACK" in str(result.reason)


def test_url_policy_detects_dns_rebinding_before_network_use() -> None:
    from app.security.url_policy import validate_redirect_chain

    sequence = [["93.184.216.34"], ["127.0.0.1"]]
    result = validate_redirect_chain(
        "https://rebind.example.test/report",
        [],
        resolver=lambda _: sequence.pop(0),
    )
    assert result.allowed is False
    assert result.reason == "DNS_REBINDING"


def test_llm_payload_contract_rejects_extra_fields_boolean_numbers_and_invalid_json() -> None:
    from app.providers.llm.contracts import FactExtractionEnvelope, parse_structured_output

    with pytest.raises(ValueError):
        parse_structured_output('{"schema_version":"llm-extraction-v1",', FactExtractionEnvelope)
    with pytest.raises(ValueError):
        parse_structured_output(
            {
                "schema_version": "llm-extraction-v1",
                "prompt_version": "v1",
                "facts": [],
                "tool_calls": ["run"],
            },
            FactExtractionEnvelope,
        )
    parsed = parse_structured_output(
        {
            "schema_version": "llm-extraction-v1",
            "prompt_version": "v1",
            "facts": [{"fact_type": "metric", "numeric_value": True, "evidence_excerpt": "x"}],
        },
        FactExtractionEnvelope,
    )
    # Boolean values must never reach numeric calculation as a Python bool.
    assert not isinstance(parsed.facts[0].numeric_value, bool)


def test_diagnostics_and_job_errors_redact_secrets_and_bound_payloads() -> None:
    from app.jobs.queue import sanitize_error
    from app.observability.diagnostics import lineage_event

    error = sanitize_error("provider failed Bearer super-secret-token")
    assert "super-secret-token" not in error
    event = lineage_event(
        run_id="run-1",
        stage="retrieve",
        status="FAILED",
        prompt="private prompt",
        api_key="secret",
    )
    assert event["prompt"] == "[REDACTED]"
    assert event["api_key"] == "[REDACTED]"


def test_request_models_reject_oversized_report_and_company_payloads() -> None:
    from app.api.companies import ResolveCompanyRequest
    from app.domain.reports.models import CreateReportRequest

    with pytest.raises(ValidationError):
        CreateReportRequest(title="x" * 181, subject={"query": "Acme"})
    with pytest.raises(ValidationError):
        ResolveCompanyRequest(query="Acme", candidates=[{}] * 101)


@pytest.mark.parametrize(
    ("budget_field", "usage_field", "reason"),
    [
        ("max_pages", "pages", "PAGE_LIMIT_EXCEEDED"),
        ("max_searches", "searches", "SEARCH_LIMIT_EXCEEDED"),
        ("max_deep_research_calls", "deep_research_calls", "DEEP_RESEARCH_CALL_LIMIT_EXCEEDED"),
        ("max_follow_up_loops", "follow_up_loops", "FOLLOW_UP_LOOP_LIMIT_EXCEEDED"),
    ],
)
def test_run_quotas_fail_closed_and_preserve_partial_state(
    budget_field: str, usage_field: str, reason: str
) -> None:
    from uuid import UUID

    from app.domain.research.models import ResearchBudget, RunStage
    from app.domain.research.service import ResearchRunService

    service = ResearchRunService()
    run = service.create_run(
        report_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        owner_user_id="quota-user",
        idempotency_key=f"quota-{budget_field}",
        budget=ResearchBudget(**{budget_field: 0}),
    )
    service.start(run.run_id, stage=RunStage.PLANNING)
    decision = service.consume_budget(run.run_id, **{usage_field: 1})
    assert decision.allowed is False
    assert decision.reason_code == reason
    assert service.get_run(run.run_id).status == "PARTIAL"


def test_frontend_does_not_embed_server_secrets() -> None:
    frontend_root = Path(__file__).resolve().parents[3] / "frontend"
    forbidden = ("SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL", "FIRECRAWL_API_KEY", "LLM_API_KEY")
    for path in frontend_root.rglob("*.ts*"):
        if "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert not any(secret in text for secret in forbidden), path
