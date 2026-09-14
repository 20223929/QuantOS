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

    def list_events(
        self,
        *,
        event_type: str | None = None,
        aggregate_id: str | None = None,
        event_id: str | None = None,
        limit: int = 100,
    ) -> list[ExecutionEventProjectionModel]:
        if limit <= 0:
            raise ValueError("limit must be positive")

        statement = select(ExecutionEventProjectionModel)
        if event_type:
            statement = statement.where(ExecutionEventProjectionModel.event_type == event_type)
        if aggregate_id:
            statement = statement.where(ExecutionEventProjectionModel.aggregate_id == aggregate_id)
        if event_id:
            statement = statement.where(ExecutionEventProjectionModel.event_id == event_id)

        statement = statement.order_by(ExecutionEventProjectionModel.id.desc()).limit(limit)
        rows = list(self.session.scalars(statement))
        rows.reverse()
        return rows
