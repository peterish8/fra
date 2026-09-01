"""Safe wrapper for injected public extraction adapters."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, Protocol

from app.providers.contracts import (
    ExtractionCapability,
    ProviderResult,
    ProviderStatus,
    normalize_provider_result,
)
from app.security.url_policy import (
    Resolver,
    resolve_hostname,
    validate_redirect_chain,
    validate_url,
)

DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_RESPONSE_BYTES = 2_000_000
DEFAULT_MAX_REDIRECTS = 3


class SitePolicyDecision:
    """Decision returned by a robots/terms/site-policy integration seam."""

    def __init__(self, *, allowed: bool, reason: str | None = None) -> None:
        self.allowed = allowed
        self.reason = reason


class SitePolicyChecker(Protocol):
    def __call__(self, url: str) -> SitePolicyDecision | Mapping[str, Any]: ...


def default_site_policy_checker(url: str) -> SitePolicyDecision:
    """Fail closed until a caller supplies a policy-aware checker.

    This intentionally does not attempt to bypass robots, terms, login,
    CAPTCHA, or other access controls.  A deployment can inject a checker
    backed by its approved policy/robots implementation.
    """

    del url
    return SitePolicyDecision(allowed=False, reason="SITE_POLICY_UNCONFIRMED")


class PublicExtractor(Protocol):
    provider: str

    def extract(self, url: str, **kwargs: Any) -> ProviderResult: ...


class SafeExtractionAdapter:
    """Validate public egress and bounded extraction controls before calling an adapter."""

    def __init__(
        self,
        adapter: ExtractionCapability,
        *,
        resolver: Resolver = resolve_hostname,
        site_policy_checker: SitePolicyChecker = default_site_policy_checker,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")
        if max_redirects < 0:
            raise ValueError("max_redirects cannot be negative")
        self.adapter = adapter
        self.provider = getattr(adapter, "provider", adapter.__class__.__name__)
        self.estimated_cost_usd = getattr(adapter, "estimated_cost_usd", 0)
        self.resolver = resolver
        self.site_policy_checker = site_policy_checker
        self.timeout_seconds = float(timeout_seconds)
        self.max_response_bytes = int(max_response_bytes)
        self.max_redirects = int(max_redirects)

    def extract(self, url: str, **kwargs: Any) -> ProviderResult:
        if len(url.encode("utf-8")) > 2048:
            return self._restricted("URL_TOO_LARGE")
        validation = validate_url(url, resolver=self.resolver)
        if not validation.allowed:
            return self._restricted(validation.reason or "URL_NOT_ALLOWED")

        try:
            decision = self.site_policy_checker(url)
            if isinstance(decision, Mapping):
                policy_allowed = bool(decision.get("allowed", False))
                policy_reason = decision.get("reason")
            else:
                policy_allowed = bool(decision.allowed)
                policy_reason = decision.reason
        except Exception:
            policy_allowed = False
            policy_reason = "SITE_POLICY_ERROR"
        if not policy_allowed:
            return self._restricted(str(policy_reason or "SITE_POLICY_UNCONFIRMED"))

        # Do not permit callers to weaken provider-side limits.  The adapter
        # contract accepts these hints and must apply them to its HTTP client.
        bounded_kwargs = dict(kwargs)
        for key in (
            "timeout",
            "timeout_seconds",
            "max_response_bytes",
            "max_redirects",
            "allow_redirects",
            "follow_redirects",
        ):
            bounded_kwargs.pop(key, None)
        bounded_kwargs.update(
            {
                "timeout_seconds": self.timeout_seconds,
                "max_response_bytes": self.max_response_bytes,
                "max_redirects": self.max_redirects,
            }
        )
        try:
            result = self.adapter.extract(url, **bounded_kwargs)
        except TimeoutError:
            return self._failure(ProviderStatus.TIMEOUT, "UPSTREAM_TIMEOUT")
        except Exception:
            return self._failure(ProviderStatus.TEMPORARY_FAILURE, "PROVIDER_CALL_FAILED")
        if not isinstance(result, ProviderResult):
            return self._failure(ProviderStatus.PARSE_FAILED, "INVALID_NORMALIZED_RESULT")
        if result.data is not None and _size_bytes(result.data) > self.max_response_bytes:
            return self._failure(ProviderStatus.PARSE_FAILED, "RESPONSE_TOO_LARGE")

        redirect_chain = result.safe_metadata.get("redirect_chain")
        if redirect_chain is None:
            redirect_chain = result.safe_metadata.get("redirects")
        if redirect_chain is not None:
            redirects = (
                redirect_chain
                if isinstance(redirect_chain, Sequence) and not isinstance(redirect_chain, str)
                else [redirect_chain]
            )
            redirect_validation = validate_redirect_chain(
                url,
                redirects,
                resolver=self.resolver,
                max_redirects=self.max_redirects,
            )
            if not redirect_validation.allowed:
                return self._restricted(redirect_validation.reason or "REDIRECT_NOT_ALLOWED")
        return result

    def _restricted(self, reason: str) -> ProviderResult:
        return self._failure(ProviderStatus.ACCESS_RESTRICTED, reason)

    def _failure(self, status: ProviderStatus, error_code: str) -> ProviderResult:
        return normalize_provider_result(
            provider=str(self.provider),
            operation="extract",
            payload=None,
            provider_status=status,
            provider_request_id=None,
            retrieved_at="1970-01-01T00:00:00+00:00",
            latency_ms=0,
            cost_usd_estimate=Decimal("0"),
            raw_metadata={"safe_boundary": True},
            error_code=error_code,
            retry_classification=(
                "RETRYABLE"
                if status in {ProviderStatus.TIMEOUT, ProviderStatus.TEMPORARY_FAILURE}
                else "NOT_RETRYABLE"
            ),
        )


def _size_bytes(value: Any) -> int:
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    return len(json.dumps(value, default=str, ensure_ascii=False).encode("utf-8"))


__all__ = [
    "DEFAULT_MAX_REDIRECTS",
    "DEFAULT_MAX_RESPONSE_BYTES",
    "DEFAULT_TIMEOUT_SECONDS",
    "PublicExtractor",
    "SafeExtractionAdapter",
    "SitePolicyChecker",
    "SitePolicyDecision",
    "default_site_policy_checker",
]
