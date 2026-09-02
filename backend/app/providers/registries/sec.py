"""Fixture-only SEC EDGAR/XBRL financial adapter.

Transport and User-Agent/credential policy belong to infrastructure.  This
module only translates an already supplied Company Facts payload into the
normalized financial contract, which keeps default tests offline.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.financial import FinancialUnit
from app.providers.contracts import ProviderStatus
from app.providers.financial.contracts import FinancialProviderResult, normalize_financial_result

_TAG_METRICS = {
    "Revenues": "revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "SalesRevenueNet": "revenue",
    "NetIncomeLoss": "net_income",
    "Assets": "assets",
    "Liabilities": "liabilities",
    "StockholdersEquity": "equity",
    "OperatingIncomeLoss": "operating_income",
}


def parse_sec_company_facts(
    payload: Mapping[str, Any], *, cik: str | None = None
) -> list[dict[str, Any]]:
    """Extract reported US-GAAP facts while retaining filing provenance."""

    facts_root = payload.get("facts", payload)
    if not isinstance(facts_root, Mapping):
        raise ValueError("SEC facts payload must be an object")
    us_gaap = facts_root.get("us-gaap", facts_root)
    if not isinstance(us_gaap, Mapping):
        raise ValueError("SEC us-gaap facts must be an object")
    result: list[dict[str, Any]] = []
    for tag, definition in us_gaap.items():
        if not isinstance(definition, Mapping):
            continue
        metric = _TAG_METRICS.get(str(tag), str(tag).casefold())
        # The normalized financial contract intentionally bounds metric
        # identifiers. SEC taxonomy tags can be extremely verbose; omit those
        # unmappable dimensions rather than failing an otherwise usable
        # Company Facts response.
        if len(metric) > 120:
            continue
        units = definition.get("units", {})
        if not isinstance(units, Mapping):
            continue
        for unit_name, observations in units.items():
            if not isinstance(observations, list):
                continue
            for observation in observations:
                if not isinstance(observation, Mapping) or observation.get("val") is None:
                    continue
                record: dict[str, Any] = {
                    "metric": metric,
                    "raw_value": observation.get("val"),
                    "value": observation.get("val"),
                    "unit": FinancialUnit.RAW.value,
                    "currency": "USD" if str(unit_name).upper() == "USD" else None,
                    "period": _period_label(observation),
                    "accounting_basis": "GAAP"
                    if str(tag).startswith(
                        (
                            "Revenue",
                            "Sales",
                            "Net",
                            "Assets",
                            "Liabilities",
                            "Stockholders",
                            "Operating",
                        )
                    )
                    else None,
                    "entity_scope": "CONSOLIDATED",
                    "source_snapshot_id": str(observation.get("filed", "")) or None,
                    "sec_cik": cik,
                    "sec_tag": str(tag),
                    "filing_form": observation.get("form"),
                }
                result.append(record)
    return result


def normalize_sec_company_facts(
    payload: Mapping[str, Any] | None,
    *,
    cik: str | None = None,
    status: ProviderStatus | str = ProviderStatus.SUCCESS,
) -> FinancialProviderResult:
    if payload is None or ProviderStatus(status) is not ProviderStatus.SUCCESS:
        return FinancialProviderResult(
            provider="SEC",
            status=ProviderStatus(status),
            source_type="REGULATORY_FILING",
        )
    try:
        facts = parse_sec_company_facts(payload, cik=cik)
    except (TypeError, ValueError, KeyError):
        return FinancialProviderResult(
            provider="SEC",
            status=ProviderStatus.PARSE_FAILED,
            source_type="REGULATORY_FILING",
            error_code="MALFORMED_XBRL",
        )
    return normalize_financial_result(
        provider="SEC",
        payload={"facts": facts},
        official=True,
        provider_status=ProviderStatus.SUCCESS,
        source_type="REGULATORY_FILING",
    )


class SECXBRLAdapter:
    official = True
    provider = "SEC"

    def __init__(self, payload: Mapping[str, Any] | None = None) -> None:
        self.payload = payload

    def fetch(self, query: Mapping[str, str]) -> FinancialProviderResult:
        return normalize_sec_company_facts(self.payload, cik=query.get("cik"))


SecXbrlAdapter = SECXBRLAdapter
SECAdapter = SECXBRLAdapter


def _period_label(observation: Mapping[str, Any]) -> str | None:
    fp = observation.get("fp")
    fy = observation.get("fy")
    frame = observation.get("frame")
    if isinstance(frame, str) and frame.startswith("CY"):
        return frame
    if fy is not None and fp:
        return (
            f"{str(fp).upper()}{fy}"
            if str(fp).upper() == "FY"
            else f"Q{str(fp).upper().lstrip('Q')} FY{fy}"
        )
    return None


__all__ = [
    "SECAdapter",
    "SECXBRLAdapter",
    "SecXbrlAdapter",
    "normalize_sec_company_facts",
    "parse_sec_company_facts",
]
