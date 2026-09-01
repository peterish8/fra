"""Fact construction from validated extraction output."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.providers.llm.contracts import ExtractedFact, FactExtractionEnvelope

from .models import FactInput, FactRecord
from .repository import FactRepository, InMemoryFactRepository


class FactService:
    """Create typed facts without calculating or coercing unknown values."""

    def __init__(self, repository: FactRepository | None = None) -> None:
        self.repository = repository or InMemoryFactRepository()

    def create(self, fact: FactInput) -> FactRecord:
        return self.repository.save(FactRecord(**fact.model_dump()))

    def from_extracted(
        self,
        fact: ExtractedFact,
        *,
        source_snapshot_id: UUID | None = None,
        company_id: UUID | None = None,
        research_run_id: UUID | None = None,
    ) -> FactRecord:
        snapshot_id = fact.source_snapshot_id or source_snapshot_id
        if snapshot_id is None:
            raise ValueError("fact extraction must identify a source snapshot")
        return self.create(
            FactInput(
                source_snapshot_id=snapshot_id,
                company_id=company_id,
                research_run_id=research_run_id,
                fact_type=fact.fact_type,
                metric_code=fact.metric_code,
                raw_value_text=fact.raw_value_text,
                numeric_value=_decimal_or_none(fact.numeric_value),
                text_value=fact.text_value,
                currency=fact.currency,
                unit=fact.unit,
                period_start=_date_or_none(fact.period_start),
                period_end=_date_or_none(fact.period_end),
                period_label=fact.period_label,
                accounting_basis=fact.accounting_basis,
                entity_scope=fact.entity_scope,
                extraction_confidence=fact.extraction_confidence,
                metadata={
                    "evidence_excerpt": fact.evidence_excerpt,
                    "evidence_locator": fact.evidence_locator,
                },
            )
        )

    def from_envelope(
        self,
        envelope: FactExtractionEnvelope,
        *,
        source_snapshot_id: UUID | None = None,
        company_id: UUID | None = None,
        research_run_id: UUID | None = None,
    ) -> list[FactRecord]:
        return [
            self.from_extracted(
                item,
                source_snapshot_id=envelope.source_snapshot_id or source_snapshot_id,
                company_id=company_id,
                research_run_id=research_run_id,
            )
            for item in envelope.facts
        ]


def _decimal_or_none(value: str | int | float | None) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("numeric fact is not a valid decimal") from error
    if not result.is_finite():
        raise ValueError("numeric fact must be finite")
    return result


def _date_or_none(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("fact period must use ISO date format") from error


__all__ = ["FactService"]
