from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.storage.models.consumption import ConsumedExecutionEventModel


class ConsumedExecutionEventRepository:
    """Durable idempotency ledger for execution event consumers."""

    def __init__(self, session):
        self.session = session

    def mark_consumed(self, event_id: str, event_type: str, aggregate_id: str) -> bool:
        event_id = str(event_id)
        existing = self.session.scalar(
            select(ConsumedExecutionEventModel).where(
                ConsumedExecutionEventModel.event_id == event_id
            )
        )
        if existing is not None:
            return False

        record = ConsumedExecutionEventModel(
            event_id=event_id,
            event_type=str(event_type),
            aggregate_id=str(aggregate_id),
            consumed_at=datetime.now(UTC),
        )
        self.session.add(record)
        try:
            self.session.flush()
        except Exception:
            self.session.rollback()
            existing = self.session.scalar(
                select(ConsumedExecutionEventModel).where(
                    ConsumedExecutionEventModel.event_id == event_id
                )
            )
            return existing is None
        return True
