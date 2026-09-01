"""Authenticated current-user route."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.security.auth import AuthenticatedUser, get_current_user


class MeResponse(BaseModel):
    id: str
    email: str | None = None


router = APIRouter(prefix="/v1", tags=["identity"])
_current_user_dependency = Depends(get_current_user)


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: AuthenticatedUser = _current_user_dependency) -> MeResponse:
    return MeResponse(id=current_user.id, email=current_user.email)


__all__ = ["MeResponse", "get_me", "router"]
