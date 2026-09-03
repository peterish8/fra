"""Small persistence seam for user-owned thesis points.

The in-memory implementation powers fixture mode only. The accompanying SQL
schema defines the PostgreSQL representation for deployment.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from .models import ThesisPoint, ThesisPointCreate, ThesisPointUpdate


class AnalystWorkflowRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, list[ThesisPoint]] = defaultdict(list)
        self._lock = threading.RLock()

    def list_thesis_points(self, report_id: UUID) -> list[ThesisPoint]:
        with self._lock:
            return list(self._items[report_id])

    def create_thesis_point(self, report_id: UUID, payload: ThesisPointCreate) -> ThesisPoint:
        point = ThesisPoint(
            report_id=report_id,
            statement=payload.statement,
            falsifier=payload.falsifier,
            materiality=payload.materiality,
        )
        with self._lock:
            self._items[report_id].append(point)
        return point

    def update_thesis_point(
        self,
        report_id: UUID,
        thesis_point_id: UUID,
        payload: ThesisPointUpdate,
    ) -> ThesisPoint | None:
        with self._lock:
            for index, item in enumerate(self._items[report_id]):
                if item.thesis_point_id != thesis_point_id:
                    continue
                updated = item.model_copy(
                    update={
                        "status": payload.status,
                        "review_note": payload.review_note,
                        "linked_claim_version_ids": payload.linked_claim_version_ids,
                        "updated_at": datetime.now(UTC),
                    }
                )
                self._items[report_id][index] = updated
                return updated
        return None


__all__ = ["AnalystWorkflowRepository"]
