"""Report workspace domain boundary."""

from .models import (
    CreateReportRequest,
    ReportDepth,
    ReportDetail,
    ReportListResponse,
    ReportRecord,
    ReportStatus,
    ReportSubject,
    ReportSummary,
    ResearchMode,
)
from .repository import (
    FixtureReportRepositoryAdapter,
    IdempotencyConflictError,
    InMemoryReportRepository,
    ReportRepository,
    ReportRepositoryUnavailable,
    adapt_report_repository,
)
from .service import InvalidReportCursor, ReportService

__all__ = [
    "CreateReportRequest",
    "FixtureReportRepositoryAdapter",
    "IdempotencyConflictError",
    "InMemoryReportRepository",
    "InvalidReportCursor",
    "ReportDepth",
    "ReportDetail",
    "ReportListResponse",
    "ReportRecord",
    "ResearchMode",
    "ReportRepository",
    "ReportRepositoryUnavailable",
    "ReportService",
    "ReportStatus",
    "ReportSubject",
    "ReportSummary",
    "adapt_report_repository",
]
