from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domain.comparisons import compare_companies

router = APIRouter(prefix="/v1/comparisons", tags=["comparisons"])


class ComparisonRequest(BaseModel):
    companies: list[dict[str, Any]] = Field(min_length=2)
    metrics: list[str] | None = None


class ComparisonResponse(BaseModel):
    companies: list[str]
    cohort: str
    metrics: list[dict[str, Any]]
    warnings: list[str]


@router.post("", response_model=ComparisonResponse)
async def create_comparison(payload: ComparisonRequest) -> ComparisonResponse:
    return ComparisonResponse.model_validate(compare_companies(payload.companies, payload.metrics))


__all__ = ["ComparisonRequest", "ComparisonResponse", "create_comparison", "router"]
