"""Deterministic, citation-required analyst projections for fixture mode."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.domain.reports.models import ReportRecord

from .models import (
    ChangeBrief,
    ChangeBriefItem,
    ChangeBriefKind,
    ChangeDirection,
    EvidenceCitation,
    Tearsheet,
    TearsheetSection,
    ThesisPoint,
)

_FIXTURE_SNAPSHOT = UUID("00000000-0000-4000-8000-000000000001")


def _citation(label: str, excerpt: str) -> EvidenceCitation:
    return EvidenceCitation(
        source_snapshot_id=_FIXTURE_SNAPSHOT,
        source_label=label,
        excerpt=excerpt,
        retrieved_at=datetime.now(UTC),
    )


def build_change_brief(report: ReportRecord, kind: ChangeBriefKind) -> ChangeBrief:
    company = report.subject.query
    document = (
        "latest earnings materials"
        if kind == ChangeBriefKind.EARNINGS
        else "latest filing snapshot"
    )
    return ChangeBrief(
        report_id=report.report_id,
        kind=kind,
        title=f"{company} — {kind.value.title()} change brief",
        as_of=datetime.now(UTC),
        limitations=[
            (
                "Fixture projection only: no live filing, estimate, price, or provider retrieval "
                "occurred."
            ),
            (
                "Each production change item must map to stored claim versions and retained source "
                "snapshots."
            ),
        ],
        items=[
            ChangeBriefItem(
                direction=ChangeDirection.UPDATED,
                headline=f"Review the change in {document}",
                why_it_matters=(
                    "A change brief highlights what needs analyst review; it does not infer "
                    "a financial conclusion without linked facts."
                ),
                citations=[
                    _citation(
                        "Fixture source ledger",
                        "Source snapshot fixture used to demonstrate cited change rendering.",
                    )
                ],
            ),
            ChangeBriefItem(
                direction=ChangeDirection.NEW_RISK,
                headline="Check guidance, definitions, and comparability before summarizing",
                why_it_matters=(
                    "A period, currency, scope, or accounting-definition change can look "
                    "like a value change when it is not comparable."
                ),
                citations=[
                    _citation(
                        "Fixture verification policy",
                        "Comparison requires period, currency, method, and entity-scope checks.",
                    )
                ],
            ),
        ],
    )


def build_tearsheet(report: ReportRecord, thesis_points: list[ThesisPoint]) -> Tearsheet:
    company = report.subject.query
    thesis_summary = (
        f"{len(thesis_points)} thesis point(s) are being tracked separately from factual verdicts."
        if thesis_points
        else (
            "No thesis points have been added; add a claim to test and a condition that would "
            "falsify it."
        )
    )
    citation = _citation(
        "Fixture report lineage",
        "This fixture tearsheet demonstrates the required citation envelope.",
    )
    return Tearsheet(
        report_id=report.report_id,
        title=f"{company} — research tearsheet",
        as_of=datetime.now(UTC),
        research_mode=getattr(report, "research_mode", "INITIATION"),
        sections=[
            TearsheetSection(
                label="Research posture",
                summary="Evidence-led research workspace; this is not investment advice.",
                citations=[citation],
            ),
            TearsheetSection(
                label="What changed",
                summary=(
                    "Use the cited change brief to isolate additions, updates, and newly "
                    "visible risks."
                ),
                citations=[citation],
            ),
            TearsheetSection(label="Thesis monitor", summary=thesis_summary, citations=[citation]),
        ],
        open_questions=["Which material claims still lack independent source-family coverage?"],
        limitations=["Fixture-only projection. It does not contain live provider or market data."],
    )


__all__ = ["build_change_brief", "build_tearsheet"]
