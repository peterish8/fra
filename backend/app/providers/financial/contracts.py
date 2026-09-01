"""Replaceable, provider-neutral financial retrieval contracts."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.domain.financial import FinancialUnit, normalize_financial_value
from app.providers.contracts import ProviderStatus


class FinancialFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1, max_length=120)
    raw_value: str | int | float | Decimal | None = None
    value: Decimal | None = None
    normalized_value: Decimal | None = None
    unit: FinancialUnit = FinancialUnit.RAW
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    normalized_unit: FinancialUnit = FinancialUnit.RAW
    normalized_currency: str | None = Field(default=None, min_length=3, max_length=3)
    period: str | None = None
    entity_scope: str | None = None
    accounting_basis: str | None = None
    source_snapshot_id: str | None = None
    provider_request_id: str | None = None
    provider: str = Field(min_length=1)
    official: bool = False


class FinancialProviderResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    status: ProviderStatus | str
    facts: list[FinancialFact] = Field(default_factory=list)
    source_type: str = "FINANCIAL_API"
    provider_request_id: str | None = None
    retrieved_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    latency_ms: float = Field(default=0, ge=0)
    cost_usd_estimate: Decimal = Field(default=Decimal("0"), ge=0)
    safe_metadata: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    reason: str | None = None
    retryable: bool = False
    retry_class: str = "NOT_RETRYABLE"
    cost: Decimal = Decimal("0")


class FinancialProvider(Protocol):
    provider: str
    official: bool

    def fetch(self, query: Mapping[str, str]) -> FinancialProviderResult:
        """Return a normalized result without exposing provider payloads."""


def normalize_financial_result(
    *,
    provider: str,
    payload: Mapping[str, Any] | None,
    official: bool = False,
    provider_status: ProviderStatus | str = ProviderStatus.SUCCESS,
    source_type: str = "FINANCIAL_API",
) -> FinancialProviderResult:
    """Normalize fixture/provider records and preserve explicit failures."""

    status = ProviderStatus(provider_status)
    if status is not ProviderStatus.SUCCESS or payload is None:
        return FinancialProviderResult(
            provider=provider,
            status=status,
            source_type=source_type,
            reason=f"{provider} returned {status.value.lower()}.",
        )
    raw_facts = payload.get("facts", payload.get("data", []))
    if not isinstance(raw_facts, list):
        return FinancialProviderResult(
            provider=provider,
            status=ProviderStatus.PARSE_FAILED,
            source_type=source_type,
            error_code="MALFORMED_FACTS",
            reason="Financial provider facts must be a list.",
        )
    facts: list[FinancialFact] = []
    try:
        for raw in raw_facts:
            if not isinstance(raw, Mapping):
                raise ValueError("financial fact must be an object")
            metric = str(raw.get("metric", raw.get("metric_code", ""))).strip()
            normalized = normalize_financial_value(
                raw.get("value", raw.get("raw_value")),
                unit=raw.get("unit"),
                currency=raw.get("currency"),
                period=raw.get("period", raw.get("period_label")),
            )
            facts.append(
                FinancialFact(
                    metric=metric,
                    raw_value=raw.get("raw_value", raw.get("value")),
                    value=normalized.original_value,
                    normalized_value=normalized.normalized_value,
                    unit=normalized.original_unit,
                    currency=normalized.original_currency,
                    normalized_unit=normalized.normalized_unit,
                    normalized_currency=normalized.normalized_currency,
                    period=raw.get("period", raw.get("period_label")),
                    entity_scope=raw.get("entity_scope"),
                    accounting_basis=raw.get("accounting_basis"),
                    source_snapshot_id=(
                        str(raw["source_snapshot_id"])
                        if raw.get("source_snapshot_id") is not None
                        else None
                    ),
                    provider_request_id=(
                        str(raw["provider_request_id"])
                        if raw.get("provider_request_id") is not None
                        else None
                    ),
                    provider=provider,
                    official=official,
                )
            )
    except (TypeError, ValueError, KeyError):
        return FinancialProviderResult(
            provider=provider,
            status=ProviderStatus.PARSE_FAILED,
            source_type=source_type,
            error_code="MALFORMED_FACT",
            reason="Financial provider returned an unparseable fact.",
        )
    return FinancialProviderResult(
        provider=provider,
        status=ProviderStatus.SUCCESS,
        source_type=source_type,
        facts=facts,
    )


__all__ = [
    "FinancialFact",
    "FinancialProvider",
    "FinancialProviderResult",
    "ProviderStatus",
    "normalize_financial_result",
]
