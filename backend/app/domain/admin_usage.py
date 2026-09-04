"""Read-only administrative usage projections.

The production implementation will be backed by durable quota and audit data.
Until that store is connected, only development and test application factories
receive the explicitly labelled fixture repository below.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class QuotaStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    NEARING_LIMIT = "NEARING_LIMIT"
    AT_LIMIT = "AT_LIMIT"


class AdminUserUsage(BaseModel):
    """Privacy-minimised per-user research quota summary."""

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1, max_length=120)
    role: Literal["USER", "ADMIN"]
    research_runs_used: int = Field(ge=0)
    research_runs_limit: int = Field(ge=1)
    quota_status: QuotaStatus


class AdminUsageOverview(BaseModel):
    """Safe operational overview exposed only through the admin boundary."""

    model_config = ConfigDict(frozen=True)

    data_mode: Literal["FIXTURE", "LIVE"]
    generated_at: datetime
    observation_window_hours: int = Field(ge=1, le=168)
    registered_users: int = Field(ge=0)
    active_users_in_window: int = Field(ge=0)
    research_runs_in_window: int = Field(ge=0)
    users: tuple[AdminUserUsage, ...]


class AdminUsageRepository(Protocol):
    """Repository boundary for aggregated admin-only operational data."""

    def get_overview(self) -> AdminUsageOverview: ...


class FixtureAdminUsageRepository:
    """Deterministic, non-production data used only by local preview and tests."""

    def get_overview(self) -> AdminUsageOverview:
        users = (
            AdminUserUsage(
                user_id="local-admin",
                display_name="Local administrator",
                role="ADMIN",
                research_runs_used=4,
                research_runs_limit=25,
                quota_status=QuotaStatus.AVAILABLE,
            ),
            AdminUserUsage(
                user_id="local-analyst",
                display_name="Local research analyst",
                role="USER",
                research_runs_used=8,
                research_runs_limit=12,
                quota_status=QuotaStatus.NEARING_LIMIT,
            ),
            AdminUserUsage(
                user_id="fixture-reviewer",
                display_name="Fixture review account",
                role="USER",
                research_runs_used=10,
                research_runs_limit=10,
                quota_status=QuotaStatus.AT_LIMIT,
            ),
        )
        return AdminUsageOverview(
            data_mode="FIXTURE",
            generated_at=datetime.now(UTC),
            observation_window_hours=24,
            registered_users=len(users),
            active_users_in_window=len(users),
            research_runs_in_window=sum(user.research_runs_used for user in users),
            users=users,
        )


__all__ = [
    "AdminUsageOverview",
    "AdminUsageRepository",
    "AdminUserUsage",
    "FixtureAdminUsageRepository",
    "QuotaStatus",
]
