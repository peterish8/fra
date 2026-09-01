"""Authenticated company/entity resolution endpoint."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.companies import EntityQuery, EntityResolution, resolve_entity
from app.security.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/v1/companies", tags=["companies"])
_current_user_dependency = Depends(get_current_user)


class ResolveCompanyRequest(BaseModel):
    """Fixture-compatible request; candidates are temporary input until storage exists."""

    model_config = ConfigDict(extra="ignore")

    query: str | EntityQuery
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    domain: str | None = Field(default=None, max_length=253)
    ticker: str | None = Field(default=None, max_length=64)
    exchange: str | None = Field(default=None, max_length=64)
    registry: str | None = Field(default=None, max_length=100)
    registry_id: str | None = Field(default=None, max_length=200)
    candidates: list[dict[str, Any]] = Field(default_factory=list, max_length=100)

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


@router.post("/resolve", response_model=EntityResolution)
async def resolve_company(
    payload: ResolveCompanyRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, _current_user_dependency],
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> EntityResolution:
    """Resolve supplied fixture candidates through the existing auth boundary."""

    del request, current_user, x_request_id
    query: EntityQuery
    if isinstance(payload.query, EntityQuery):
        query = payload.query
    else:
        query = EntityQuery.model_validate(
            {
                "name": payload.query,
                "country_code": payload.country_code,
                "domain": payload.domain,
                "ticker": payload.ticker,
                "exchange": payload.exchange,
                "registry": payload.registry,
                "registry_id": payload.registry_id,
            }
        )
    return resolve_entity(query=query, candidates=payload.candidates)


def include_company_router(application: object) -> None:
    """Install the company router from an application factory."""

    include_router = getattr(application, "include_router", None)
    if not callable(include_router):
        raise TypeError("application must provide include_router")
    include_router(router)


__all__ = ["ResolveCompanyRequest", "include_company_router", "resolve_company", "router"]
