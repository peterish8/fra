"""Health- and budget-aware routing over normalized provider capabilities."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.providers.contracts import (
    ExtractionCapability,
    ProviderResult,
    ProviderStatus,
    SearchCapability,
    normalize_provider_result,
)
from app.security.url_policy import validate_url

DEFAULT_SEARCH_ORDER = ("perplexity", "brave", "exa")
DEFAULT_EXTRACTION_ORDER = ("firecrawl", "exa_contents", "permitted_browser")
_SKIP_HEALTH = {"UNHEALTHY", "DISABLED", "OFFLINE", "OPEN_CIRCUIT"}
_FORBIDDEN_EXTRACTION_OPTIONS = {
    "auth",
    "authorization",
    "bypass",
    "captcha",
    "cookie",
    "cookies",
    "session",
}


def _decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default
    return result if result >= 0 else default


def _provider_name(provider: Any) -> str:
    value = getattr(provider, "provider", None) or getattr(provider, "provider_name", None)
    return str(value or provider.__class__.__name__).strip().lower()


def _estimated_cost(provider: Any) -> Decimal:
    for name in ("estimated_cost_usd", "cost_usd_estimate", "estimated_cost"):
        if hasattr(provider, name):
            return _decimal(getattr(provider, name))
    return Decimal("0")


def _ordered(providers: Sequence[Any], configured_order: Sequence[str]) -> list[Any]:
    rank = {name.strip().lower(): index for index, name in enumerate(configured_order)}
    ordered = sorted(
        enumerate(providers),
        key=lambda item: (rank.get(_provider_name(item[1]), len(rank)), item[0]),
    )
    return [provider for _, provider in ordered]


def _safe_extraction_kwargs(kwargs: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in kwargs.items()
        if key.strip().lower() not in _FORBIDDEN_EXTRACTION_OPTIONS
    }


class ProviderRouter:
    """Route search/extraction through injected adapters.

    No adapters are created by this class.  Consequently constructing the
    router or using it without injected providers performs no live call.
    """

    def __init__(
        self,
        *,
        search_providers: Sequence[SearchCapability] | None = None,
        extraction_providers: Sequence[ExtractionCapability] | None = None,
        health_state: Mapping[str, str] | None = None,
        remaining_cost_usd: Decimal | int | float | str | None = None,
        search_order: Sequence[str] | None = None,
        extraction_order: Sequence[str] | None = None,
        url_validator: Callable[[str], Any] | None = None,
    ) -> None:
        self.search_providers = list(search_providers or [])
        self.extraction_providers = list(extraction_providers or [])
        self.health_state = {
            str(name).strip().lower(): str(state).strip().upper()
            for name, state in (health_state or {}).items()
        }
        self.remaining_cost_usd = (
            None if remaining_cost_usd is None else _decimal(remaining_cost_usd)
        )
        self.search_order = tuple(search_order or DEFAULT_SEARCH_ORDER)
        self.extraction_order = tuple(extraction_order or DEFAULT_EXTRACTION_ORDER)
        # Extraction must be safe by construction.  Callers may inject a
        # deterministic validator for tests or a stricter egress policy, but
        # omitting one always uses the SSRF-safe URL policy.
        self.url_validator = url_validator or validate_url

    def search(self, query: str, **kwargs: Any) -> ProviderResult:
        """Try configured search providers in health and budget order."""

        return self._run(
            operation="search",
            providers=_ordered(self.search_providers, self.search_order),
            argument=query,
            kwargs=kwargs,
        )

    def extract(self, url: str, **kwargs: Any) -> ProviderResult:
        """Validate before every adapter call, then use safe fallbacks."""

        return self._run(
            operation="extract",
            providers=_ordered(self.extraction_providers, self.extraction_order),
            argument=url,
            kwargs=_safe_extraction_kwargs(kwargs),
        )

    def _run(
        self,
        *,
        operation: str,
        providers: Sequence[Any],
        argument: str,
        kwargs: Mapping[str, Any],
    ) -> ProviderResult:
        last_result: ProviderResult | None = None
        considered = False
        for provider in providers:
            name = _provider_name(provider)
            if self.health_state.get(name, "HEALTHY") in _SKIP_HEALTH:
                continue
            cost = _estimated_cost(provider)
            if self.remaining_cost_usd is not None and cost > self.remaining_cost_usd:
                continue
            considered = True
            try:
                if operation == "extract":
                    policy_result = self._validate_extraction_url(argument)
                    if policy_result is not None:
                        return policy_result
                raw_result = getattr(provider, operation)(argument, **dict(kwargs))
                result = self._normalize_result(raw_result, name, operation)
            except TimeoutError:
                result = self._router_result(
                    ProviderStatus.TIMEOUT, "UPSTREAM_TIMEOUT", {"provider": name}
                )
            except Exception:
                # Adapter exceptions never escape with provider internals or
                # credentials.  The next configured capability gets a chance.
                result = self._router_result(
                    ProviderStatus.TEMPORARY_FAILURE,
                    "PROVIDER_CALL_FAILED",
                    {"provider": name},
                )
            last_result = result
            if self.remaining_cost_usd is not None:
                self.remaining_cost_usd = max(Decimal("0"), self.remaining_cost_usd - cost)
            if result.status is ProviderStatus.SUCCESS and result.data is not None:
                return result

        if last_result is not None:
            return last_result
        code = "NO_HEALTHY_PROVIDER" if providers and not considered else "NO_PROVIDER_CONFIGURED"
        return self._router_result(ProviderStatus.TEMPORARY_FAILURE, code, {})

    def _validate_extraction_url(self, url: str) -> ProviderResult | None:
        """Return a stable restriction result when extraction egress is unsafe."""

        try:
            validation = self.url_validator(url)
            if isinstance(validation, Mapping):
                allowed = bool(validation.get("allowed", False))
                reason = validation.get("reason")
            else:
                allowed = bool(getattr(validation, "allowed", False))
                reason = getattr(validation, "reason", None)
        except Exception:
            # A policy failure must fail closed and must not expose validator
            # internals to callers or try the adapter as a fallback.
            allowed = False
            reason = "URL_POLICY_ERROR"
        if allowed:
            return None
        return self._router_result(
            ProviderStatus.ACCESS_RESTRICTED,
            "URL_POLICY_REJECTED",
            {"url_policy_reason": str(reason or "URL_NOT_ALLOWED")},
        )

    @staticmethod
    def _normalize_result(raw_result: Any, provider: str, operation: str) -> ProviderResult:
        if isinstance(raw_result, ProviderResult):
            return raw_result
        if isinstance(raw_result, Mapping):
            try:
                return ProviderResult.model_validate(raw_result)
            except Exception:
                pass
        return ProviderRouter._router_result(
            ProviderStatus.PARSE_FAILED,
            "INVALID_NORMALIZED_RESULT",
            {"provider": provider, "operation": operation},
        )

    @staticmethod
    def _router_result(
        status: ProviderStatus,
        error_code: str,
        metadata: Mapping[str, Any],
    ) -> ProviderResult:
        return normalize_provider_result(
            provider="router",
            operation="routing",
            payload=None,
            provider_status=status,
            provider_request_id=None,
            retrieved_at=datetime.now(UTC),
            latency_ms=0,
            cost_usd_estimate="0",
            raw_metadata=metadata,
            error_code=error_code,
            retry_classification=(
                "RETRYABLE"
                if status
                in {
                    ProviderStatus.TIMEOUT,
                    ProviderStatus.TEMPORARY_FAILURE,
                    ProviderStatus.RATE_LIMITED,
                }
                else "NOT_RETRYABLE"
            ),
        )


__all__ = [
    "DEFAULT_EXTRACTION_ORDER",
    "DEFAULT_SEARCH_ORDER",
    "ProviderRouter",
]
