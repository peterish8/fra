"""Validated server configuration.

Settings are intentionally server-only.  Secret values use ``SecretStr`` so
their normal representation cannot accidentally appear in diagnostics.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _validate_http_url(value: str) -> str:
    """Validate and normalize an application URL without retaining a slash."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("must be a non-empty HTTP or HTTPS URL")
    candidate = value.strip()
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("must be a valid HTTP or HTTPS URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("must not contain credentials, query parameters, or fragments")
    return candidate.rstrip("/")


HttpUrlString = Annotated[str, AfterValidator(_validate_http_url)]


class Settings(BaseSettings):
    """Typed environment-backed settings for the API process."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_env: Literal["development", "test", "staging", "production"]
    app_base_url: HttpUrlString
    api_base_url: HttpUrlString

    supabase_url: HttpUrlString
    supabase_anon_key: SecretStr
    supabase_service_role_key: SecretStr
    database_url: SecretStr

    perplexity_api_key: SecretStr
    brave_search_api_key: SecretStr
    exa_api_key: SecretStr
    firecrawl_api_key: SecretStr
    gemini_api_key: SecretStr
    browserless_api_key: SecretStr | None = None
    zyte_api_key: SecretStr | None = None
    apify_api_token: SecretStr | None = None
    eodhd_api_key: SecretStr | None = None
    twelve_data_api_key: SecretStr | None = None
    companies_house_api_key: SecretStr | None = None
    open_corporates_api_key: SecretStr | None = None

    llm_api_key: SecretStr
    llm_provider: str
    llm_model_extractor: str
    llm_model_verifier: str
    llm_model_synthesizer: str

    sentry_dsn: HttpUrlString | None = None
    otel_exporter_otlp_endpoint: HttpUrlString | None = None

    max_provider_cost_usd_per_research_run: float
    max_deep_research_cost_usd_per_run: float
    max_follow_up_loops: int

    # Supabase currently supports signed JWTs whose verification key is held
    # by the server.  This is optional in fixture/test settings because tests
    # can inject a deterministic verifier through ``create_app``.
    supabase_jwt_secret: SecretStr | None = None
    supabase_jwt_issuer: HttpUrlString | None = None
    supabase_jwt_audience: str = "authenticated"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once per process from the server environment."""

    return Settings()


__all__ = ["HttpUrlString", "Settings", "get_settings"]
