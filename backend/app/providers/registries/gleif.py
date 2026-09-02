"""Public GLEIF LEI lookup adapter.

GLEIF publishes a JSON API for legal-entity identifiers.  This adapter only
supports direct LEI lookups, keeps transport injectable for tests, and maps
the response into the registry-normalization contract without exposing raw
provider payloads to domain code.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .contracts import NormalizedRegistryResult, ProviderStatus, normalize_registry_result


class GLEIFHttpAdapter:
    """Keyless GLEIF adapter for direct LEI lookups."""

    provider = "GLEIF"

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        base_url: str = "https://api.gleif.org/api/v1",
        transport: Callable[[Request, float], bytes] | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("GLEIF timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")
        self._transport = transport or _urlopen_bytes

    def lookup(self, query: Mapping[str, str]) -> Mapping[str, Any] | None:
        """Return a canonical raw mapping for a direct LEI query."""

        payload, status = self._fetch(query)
        if status is not ProviderStatus.SUCCESS or payload is None:
            return None
        return _canonical_record(payload)

    def resolve(
        self,
        query: Mapping[str, str],
        *,
        as_of: str | datetime | None = None,
        freshness_policy_days: int = 30,
    ) -> NormalizedRegistryResult:
        """Fetch and normalize a GLEIF record for domain consumption."""

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
        lei = _normalize_lei(query.get("lei"))
        if lei is None:
            return None, ProviderStatus.NO_RESULTS
        request = Request(
            f"{self.base_url}/lei-records/{quote(lei, safe='')}",
            headers={"Accept": "application/vnd.api+json, application/json"},
            method="GET",
        )
        try:
            payload = json.loads(self._transport(request, self.timeout_seconds).decode("utf-8"))
        except HTTPError as error:
            return None, _gleif_http_status(error.code)
        except (TimeoutError, URLError, OSError):
            return None, ProviderStatus.TEMPORARY_FAILURE
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            return None, ProviderStatus.PARSE_FAILED
        if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), Mapping):
            return None, ProviderStatus.PARSE_FAILED
        return payload, ProviderStatus.SUCCESS


def _normalize_lei(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    return candidate if re.fullmatch(r"[A-Z0-9]{20}", candidate) else None


def _canonical_record(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    data = payload.get("data")
    if not isinstance(data, Mapping):
        return None
    attributes = data.get("attributes")
    if not isinstance(attributes, Mapping):
        return None
    entity = attributes.get("entity")
    if not isinstance(entity, Mapping):
        entity = {}
    legal_name = entity.get("legalName")
    if isinstance(legal_name, Mapping):
        legal_name = legal_name.get("name")
    legal_address = entity.get("legalAddress")
    country = legal_address.get("country") if isinstance(legal_address, Mapping) else None
    registration = attributes.get("registration")
    if not isinstance(registration, Mapping):
        registration = {}
    lei = data.get("id")
    return {
        "legal_name": legal_name,
        "registration_number": lei,
        "lei": lei,
        "jurisdiction": country,
        "legal_status": registration.get("status"),
        "incorporation_date": registration.get("initialRegistrationDate"),
    }


def _gleif_http_status(code: int) -> ProviderStatus:
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
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed GLEIF URL
        return cast(bytes, response.read())


__all__ = ["GLEIFHttpAdapter"]
