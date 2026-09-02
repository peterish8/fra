"""Owner-authorized report score and explainability endpoints.

The HTTP layer deliberately does not calculate scores.  Score engines persist
immutable, versioned snapshots and expose a small read projection through the
``score_repository`` application seam.  This keeps arithmetic and scoring
policy in the domain while ensuring that a user can only inspect scores for a
report they own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import assert_owner
from app.domain.reports import (
    ReportRepository,
    ReportRepositoryUnavailable,
    adapt_report_repository,
)
from app.security.auth import AuthenticatedUser, get_current_user
from app.security.errors import stable_http_error

router = APIRouter(prefix="/v1/reports", tags=["scoring"])
_current_user_dependency = Depends(get_current_user)


class ScoreCard(BaseModel):
    """A score plus enough context for a reader to audit its meaning."""

    model_config = ConfigDict(extra="allow")

    score: float | None = Field(default=None, ge=0, le=100)
    status: str = Field(default="NOT_ENOUGH_DATA", min_length=1)
    method: str = Field(default="deterministic", min_length=1)
    method_version: str = Field(default="unknown", min_length=1)
    coverage: float | None = Field(default=None, ge=0, le=100)
    breakdown: dict[str, Any] = Field(default_factory=dict)
    drilldown: list[dict[str, Any]] = Field(default_factory=list)
    input_ids: list[str] = Field(default_factory=list)
    config_hash: str | None = None
    score_version: str | None = None


class ScoreBreakdownResponse(BaseModel):
    """Company-level score-card projection with no universal trust score."""

    model_config = ConfigDict(extra="forbid")

    company_id: str
    research_confidence: ScoreCard
    evidence_coverage: ScoreCard
    disclosure_reliability: ScoreCard
    business_score: ScoreCard | None = None


class ReportScoreResponse(BaseModel):
    """Separate report-level score families; never a universal trust score."""

    model_config = ConfigDict(extra="forbid")

    report_id: UUID
    report_version_id: UUID | None = None
    report_version: int | None = None
    claim_confidence: ScoreCard | None = None
    research_confidence: ScoreCard
    disclosure_reliability: ScoreCard
    financial_business_score: ScoreCard
    watchlist_score: ScoreCard | None = None


class ScoreRepository(Protocol):
    """Read-only projection of persisted score snapshots for one report."""

    def get_report_scores(self, report_id: UUID) -> object | None: ...


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) and value else "req_unavailable"


def _report_repository(request: Request) -> ReportRepository:
    repository = getattr(request.app.state, "report_repository", None)
    try:
        return adapt_report_repository(repository)
    except ReportRepositoryUnavailable as error:
        raise stable_http_error(
            status_code=503,
            code="REPORT_STORE_UNAVAILABLE",
            message="Report workspace storage is not configured.",
            request_id=_request_id(request),
        ) from error


def _score_repository(request: Request) -> object:
    repository = getattr(request.app.state, "score_repository", None)
    if callable(getattr(repository, "get_report_scores", None)) or callable(
        getattr(repository, "get_scores", None)
    ):
        return repository
    raise stable_http_error(
        status_code=503,
        code="SCORE_STORE_UNAVAILABLE",
        message="Score snapshot storage is not configured.",
        request_id=_request_id(request),
    )


def _as_mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        dumped = dump()
        if isinstance(dumped, Mapping):
            return dumped
    raise TypeError("score projection must be a mapping or Pydantic model")


def _score_card(value: object, *, default_status: str = "NOT_ENOUGH_DATA") -> ScoreCard:
    if value is None:
        return ScoreCard(status=default_status)
    raw = dict(_as_mapping(value))
    # Domain snapshots have used both ``version`` and ``method_version`` while
    # the API contract intentionally exposes the latter.
    if "method_version" not in raw and "version" in raw:
        raw["method_version"] = raw["version"]
    if "method" not in raw and "score_method" in raw:
        raw["method"] = raw["score_method"]
    if "drilldown" not in raw and "explanation" in raw:
        explanation = raw["explanation"]
        raw["drilldown"] = explanation if isinstance(explanation, list) else [{"text": explanation}]
    if "input_ids" not in raw and "input_claim_ids" in raw:
        raw["input_ids"] = raw["input_claim_ids"]
    # Ignore persistence-only identifiers/timestamps; no secret or raw source
    # content belongs in this projection.
    allowed = set(ScoreCard.model_fields)
    normalized = {key: item for key, item in raw.items() if key in allowed}
    return ScoreCard.model_validate(normalized)


def _response(report_id: UUID, projection: object) -> ReportScoreResponse:
    raw = dict(_as_mapping(projection))
    if "scores" in raw and isinstance(raw["scores"], Mapping):
        scores = raw["scores"]
    else:
        scores = raw

    def pick(*names: str) -> object:
        for name in names:
            if name in scores:
                return scores[name]
        return None

    return ReportScoreResponse(
        report_id=report_id,
        report_version_id=raw.get("report_version_id"),
        report_version=raw.get("report_version"),
        claim_confidence=(
            _score_card(pick("claim_confidence", "claim_confidence_score"))
            if pick("claim_confidence", "claim_confidence_score") is not None
            else None
        ),
        research_confidence=_score_card(pick("research_confidence")),
        disclosure_reliability=_score_card(pick("disclosure_reliability")),
        financial_business_score=_score_card(
            pick("financial_business_score", "financial_score", "business_score")
        ),
        watchlist_score=(
            _score_card(pick("watchlist_score")) if pick("watchlist_score") is not None else None
        ),
    )


def _get_projection(repository: object, report_id: UUID) -> object | None:
    getter = getattr(repository, "get_report_scores", None)
    if not callable(getter):
        getter = getattr(repository, "get_scores", None)
    if not callable(getter):
        return None
    return cast(object | None, getter(report_id=report_id))


@router.get("/{report_id}/scores", response_model=ReportScoreResponse)
async def get_report_scores(
    report_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
) -> ReportScoreResponse:
    """Return explainable score snapshots after report-owner authorization."""

    report = _report_repository(request).get_report(report_id)
    if report is None or report.deleted_at is not None:
        raise stable_http_error(
            status_code=404,
            code="NOT_FOUND",
            message="The requested report was not found.",
            request_id=_request_id(request),
        )
    assert_owner(
        current_user_id=current_user.id,
        resource_owner_id=report.owner_user_id,
        request_id=_request_id(request),
    )
    projection = _get_projection(_score_repository(request), report_id)
    if projection is None:
        raise stable_http_error(
            status_code=404,
            code="SCORES_NOT_FOUND",
            message="No score snapshot is available for this report.",
            request_id=_request_id(request),
        )
    try:
        return _response(report_id, projection)
    except (TypeError, ValueError) as error:
        raise stable_http_error(
            status_code=500,
            code="SCORE_PROJECTION_INVALID",
            message="The stored score snapshot could not be read safely.",
            request_id=_request_id(request),
        ) from error


def include_score_router(application: object) -> None:
    """Install scoring routes from the application factory."""

    include_router = getattr(application, "include_router", None)
    if not callable(include_router):
        raise TypeError("application must provide include_router")
    include_router(router)


__all__ = [
    "ReportScoreResponse",
    "ScoreCard",
    "ScoreBreakdownResponse",
    "ScoreRepository",
    "get_report_scores",
    "include_score_router",
    "router",
]
