from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select

from app.storage.models.execution_projection import ExecutionEventProjectionModel


class ExecutionEventProjectionRepository:
    """Durable projection storage for consumed execution events."""

    def __init__(self, session):
        self.session = session

    def save(self, event_id: str, event_type: str, aggregate_id: str, payload: dict) -> None:
        self.session.add(
            ExecutionEventProjectionModel(
                event_id=str(event_id),
                event_type=str(event_type),
                aggregate_id=str(aggregate_id),
                payload=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                projected_at=datetime.now(UTC),
            )
        )

    def list_all(self) -> list[ExecutionEventProjectionModel]:
        return list(
            self.session.scalars(
                select(ExecutionEventProjectionModel).order_by(
                    ExecutionEventProjectionModel.id.asc()
                )
            )
        )
