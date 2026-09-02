"""Companies House public registry adapter.

Companies House provides a free developer API key for public GET requests.
The key is sent as Basic authentication to this server-side adapter only.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .contracts import NormalizedRegistryResult, ProviderStatus, normalize_registry_result


class CompaniesHouseHttpAdapter:
    """Official UK company lookup using a user-owned free API key."""

    provider = "COMPANIES_HOUSE"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 10.0,
        base_url: str = "https://api.company-information.service.gov.uk",
        transport: Callable[[Request, float], bytes] | None = None,
    ) -> None:
        if not api_key.strip() or ":" in api_key:
            raise ValueError("Companies House api_key must be non-empty and colon-free")
        if timeout_seconds <= 0:
            raise ValueError("Companies House timeout_seconds must be positive")
        self._auth = base64.b64encode(f"{api_key.strip()}:".encode()).decode("ascii")
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")
        self._transport = transport or _urlopen_bytes

    def lookup(self, query: Mapping[str, str]) -> Mapping[str, Any] | None:
        payload, status = self._fetch(query)
        return _canonical_record(payload) if status is ProviderStatus.SUCCESS else None

    def resolve(
        self,
        query: Mapping[str, str],
        *,
        as_of: str | datetime | None = None,
        freshness_policy_days: int = 30,
    ) -> NormalizedRegistryResult:
        retrieved_at = datetime.now(UTC)
        payload, status = self._fetch(query)
        return normalize_registry_result(
            provider=self.provider,
            payload=_canonical_record(payload) if payload is not None else None,
            retrieved_at=retrieved_at,
            freshness_policy_days=freshness_policy_days,
            provider_status=status,
            as_of=as_of,
        )

    def _fetch(
        self, query: Mapping[str, str]
    ) -> tuple[Mapping[str, Any] | None, ProviderStatus]:
        number = _normalize_company_number(query.get("company_number"))
        if number is None:
            return None, ProviderStatus.NO_RESULTS
        request = Request(
            f"{self.base_url}/company/{quote(number, safe='')}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {self._auth}",
            },
            method="GET",
        )
        try:
            payload = json.loads(self._transport(request, self.timeout_seconds).decode("utf-8"))
        except HTTPError as error:
            return None, _companies_house_http_status(error.code)
        except (TimeoutError, URLError, OSError):
            return None, ProviderStatus.TEMPORARY_FAILURE
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            return None, ProviderStatus.PARSE_FAILED
        if not isinstance(payload, Mapping):
            return None, ProviderStatus.PARSE_FAILED
        return payload, ProviderStatus.SUCCESS


def _normalize_company_number(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = re.sub(r"\s+", "", value).upper()
    return candidate if re.fullmatch(r"[A-Z0-9]{2,12}", candidate) else None


def _canonical_record(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    return {
        "legal_name": payload.get("company_name"),
        "registration_number": payload.get("company_number"),
        "jurisdiction": "GB",
        "legal_status": payload.get("company_status"),
        "incorporation_date": payload.get("date_of_creation"),
    }


def _companies_house_http_status(code: int) -> ProviderStatus:
    if code == 404:
        return ProviderStatus.NO_RESULTS
    if code == 429:
        return ProviderStatus.RATE_LIMITED
    if code in {401, 403}:
        return ProviderStatus.ACCESS_RESTRICTED
    if 500 <= code <= 599:
        return ProviderStatus.TEMPORARY_FAILURE
    return ProviderStatus.PERMANENT_FAILURE


def _urlopen_bytes(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed official URL
        return cast(bytes, response.read())


__all__ = ["CompaniesHouseHttpAdapter"]
