"""Stable liveness routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


def _health() -> HealthResponse:
    return HealthResponse()


router = APIRouter(tags=["health"])
versioned_router = APIRouter(prefix="/v1", tags=["health"])
router.add_api_route("/health", _health, methods=["GET"], response_model=HealthResponse)
versioned_router.add_api_route(
    "/health",
    _health,
    methods=["GET"],
    response_model=HealthResponse,
)


__all__ = ["HealthResponse", "router", "versioned_router"]
