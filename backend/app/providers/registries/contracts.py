"""Normalized contracts shared by official registry adapters and fallbacks."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProviderStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    RATE_LIMITED = "RATE_LIMITED"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    PARSE_FAILED = "PARSE_FAILED"
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"


class LegalEntityRecord(BaseModel):
    """Storage-ready legal record; persistence remains an external adapter seam."""

    model_config = ConfigDict(extra="allow")

    registry_name: str = Field(min_length=1)
    jurisdiction: str | None = None
    registration_number: str | None = None
    legal_name: str = Field(min_length=1)
    legal_status: str | None = None
    incorporation_date: str | None = None
    retrieved_at: str = Field(min_length=1)
    freshness: str = Field(pattern="^(CURRENT|STALE)$")
    source: str = Field(min_length=1)
    source_snapshot_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedRegistryResult(BaseModel):
    status: str
    legal_record: LegalEntityRecord | None = None
    reason: str | None = None


class RegistryAdapter(Protocol):
    """Provider-specific lookup interface; adapters must return raw provider data."""

    provider: str

    def lookup(self, query: Mapping[str, str]) -> Mapping[str, Any] | None: ...


_FAILURE_STATUSES = {
    ProviderStatus.NO_RESULTS.value,
    ProviderStatus.RATE_LIMITED.value,
    ProviderStatus.ACCESS_RESTRICTED.value,
    ProviderStatus.PARSE_FAILED.value,
    ProviderStatus.TEMPORARY_FAILURE.value,
    ProviderStatus.PERMANENT_FAILURE.value,
}


def normalize_registry_result(
    *,
    provider: str,
    payload: Mapping[str, Any] | None,
    retrieved_at: str | datetime,
    freshness_policy_days: int = 30,
    provider_status: ProviderStatus | str | None = None,
    as_of: str | datetime | None = None,
) -> NormalizedRegistryResult:
    """Normalize official/fallback output while retaining explicit failures.

    The function does not call a provider, persist a record, or turn an absent
    record into a negative legal conclusion. Any provider/access/parse failure
    becomes ``LEGAL_ENTITY_UNCONFIRMED`` for the domain/API boundary.
    """

    provider_name = provider.strip().upper()
    retrieved_text, retrieved_datetime = _timestamp(retrieved_at)
    status = str(
        provider_status.value
        if isinstance(provider_status, ProviderStatus)
        else provider_status or ""
    ).upper()
    if status in _FAILURE_STATUSES or payload is None:
        reason_code = status or "NO_RESULTS"
        return NormalizedRegistryResult(
            status="LEGAL_ENTITY_UNCONFIRMED",
            legal_record=None,
            reason=f"Registry provider {provider_name} returned {reason_code.lower()}.",
        )

    try:
        legal_name = _first_text(payload, "legal_name", "company_name", "name")
        registration_number = _first_text(
            payload, "registration_number", "company_number", "cin", "registration_id", "lei"
        )
        jurisdiction = _first_text(payload, "jurisdiction", "jurisdiction_code", "country_code")
        legal_status = _normalize_legal_status(
            _first_text(payload, "legal_status", "company_status", "status")
        )
        incorporation_date = _first_text(
            payload, "incorporation_date", "date_of_creation", "formed_on"
        )
        if not legal_name:
            raise ValueError("legal name is missing")
        freshness = _freshness(retrieved_datetime, as_of, freshness_policy_days)
        record = LegalEntityRecord(
            registry_name=provider_name,
            jurisdiction=jurisdiction,
            registration_number=registration_number,
            legal_name=legal_name,
            legal_status=legal_status,
            incorporation_date=incorporation_date,
            retrieved_at=retrieved_text,
            freshness=freshness,
            source=provider_name,
            metadata={"provider_status": "SUCCESS"},
        )
    except (TypeError, ValueError, KeyError):
        return NormalizedRegistryResult(
            status="LEGAL_ENTITY_UNCONFIRMED",
            legal_record=None,
            reason=f"Registry provider {provider_name} returned an unparseable legal record.",
        )
    return NormalizedRegistryResult(status="SUCCESS", legal_record=record, reason=None)


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    # GLEIF responses commonly nest legal identity under data.attributes.entity.
    data = payload.get("data")
    if isinstance(data, Mapping):
        attributes = data.get("attributes")
        if isinstance(attributes, Mapping):
            entity = attributes.get("entity")
            if isinstance(entity, Mapping):
                if "legal_name" in keys and isinstance(entity.get("legalName"), Mapping):
                    name = entity["legalName"].get("name")
                    if isinstance(name, str) and name.strip():
                        return name.strip()
                if "lei" in keys and isinstance(data.get("id"), str):
                    return str(data["id"]).strip()
                for key in keys:
                    value = entity.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
    return None


def _normalize_legal_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper().replace(" ", "_")
    return {
        "ACTIVE": "ACTIVE",
        "INACTIVE": "INACTIVE",
        "DISSOLVED": "DISSOLVED",
        "LIQUIDATED": "LIQUIDATED",
        "RETIRED": "INACTIVE",
    }.get(normalized, normalized)


def _timestamp(value: str | datetime) -> tuple[str, datetime]:
    if isinstance(value, datetime):
        parsed = value if value.tzinfo else value.replace(tzinfo=UTC)
        return value.isoformat(), parsed.astimezone(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return value, parsed.astimezone(UTC)


def _freshness(retrieved_at: datetime, as_of: str | datetime | None, policy_days: int) -> str:
    if policy_days < 0:
        raise ValueError("freshness policy must not be negative")
    if as_of is None:
        reference = retrieved_at
    else:
        _, reference = _timestamp(as_of)
    age_days = (reference - retrieved_at).total_seconds() / 86400
    return "CURRENT" if age_days <= policy_days else "STALE"


__all__ = [
    "LegalEntityRecord",
    "NormalizedRegistryResult",
    "ProviderStatus",
    "RegistryAdapter",
    "normalize_registry_result",
]
