from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.storage.models.outbox import ExecutionOutboxModel


class ExecutionOutboxRepository:
    """Durable queue for execution events created in the same DB transaction."""

    def __init__(self, session):
        self.session = session

    def enqueue(self, event_type: str, aggregate_id: str, payload: dict, event_id: str | None = None):
        event_id = str(event_id or uuid4())
        existing = self.session.scalar(
            select(ExecutionOutboxModel).where(ExecutionOutboxModel.event_id == event_id)
        )
        if existing is not None:
            return existing
        record = ExecutionOutboxModel(
            event_id=event_id,
            event_type=str(event_type),
            aggregate_id=str(aggregate_id),
            payload=json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            status="PENDING",
            attempts=0,
            created_at=datetime.now(UTC),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def pending(self, limit: int = 100):
        statement = (
            select(ExecutionOutboxModel)
            .where(ExecutionOutboxModel.status == "PENDING")
            .order_by(ExecutionOutboxModel.id)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def mark_processed(self, event_id: str):
        record = self.session.scalar(
            select(ExecutionOutboxModel).where(ExecutionOutboxModel.event_id == str(event_id))
        )
        if record is None:
            return None
        record.status = "PROCESSED"
        record.processed_at = datetime.now(UTC)
        self.session.flush()
        return record

    def mark_retry(self, event_id: str):
        record = self.session.scalar(
            select(ExecutionOutboxModel).where(ExecutionOutboxModel.event_id == str(event_id))
        )
        if record is None:
            return None
        record.status = "PENDING"
        record.attempts = int(record.attempts or 0) + 1
        self.session.flush()
        return record
