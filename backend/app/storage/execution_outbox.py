from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, or_, select, update

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

    def claim_pending(
        self,
        limit: int,
        owner: str,
        now: datetime | None = None,
        claim_seconds: int = 30,
    ):
        if limit <= 0:
            return []
        if not owner:
            raise ValueError("owner must be non-empty")
        if claim_seconds <= 0:
            raise ValueError("claim_seconds must be positive")
        now = now or datetime.now(UTC)
        expires_at = now + timedelta(seconds=claim_seconds)
        candidate_ids = list(
            self.session.scalars(
                select(ExecutionOutboxModel.id)
                .where(
                    ExecutionOutboxModel.status == "PENDING",
                    or_(
                        ExecutionOutboxModel.claim_owner.is_(None),
                        ExecutionOutboxModel.claim_expires_at.is_(None),
                        ExecutionOutboxModel.claim_expires_at <= now,
                    ),
                )
                .order_by(ExecutionOutboxModel.id)
                .limit(limit)
            )
        )
        claimed_ids = []
        for event_id in candidate_ids:
            result = self.session.execute(
                update(ExecutionOutboxModel)
                .where(
                    and_(
                        ExecutionOutboxModel.id == event_id,
                        ExecutionOutboxModel.status == "PENDING",
                        or_(
                            ExecutionOutboxModel.claim_owner.is_(None),
                            ExecutionOutboxModel.claim_expires_at.is_(None),
                            ExecutionOutboxModel.claim_expires_at <= now,
                        ),
                    )
                )
                .values(claim_owner=owner, claim_expires_at=expires_at)
            )
            if result.rowcount == 1:
                claimed_ids.append(event_id)
        self.session.flush()
        if not claimed_ids:
            return []
        return list(
            self.session.scalars(
                select(ExecutionOutboxModel)
                .where(ExecutionOutboxModel.id.in_(claimed_ids))
                .order_by(ExecutionOutboxModel.id)
            )
        )

    def mark_processed(self, event_id: str, owner: str | None = None):
        record = self.session.scalar(
            select(ExecutionOutboxModel).where(ExecutionOutboxModel.event_id == str(event_id))
        )
        if record is None:
            return None
        if owner is not None and record.claim_owner != owner:
            return None
        record.status = "PROCESSED"
        record.processed_at = datetime.now(UTC)
        record.claim_owner = None
        record.claim_expires_at = None
        self.session.flush()
        return record

    def mark_retry(self, event_id: str, owner: str | None = None):
        record = self.session.scalar(
            select(ExecutionOutboxModel).where(ExecutionOutboxModel.event_id == str(event_id))
        )
        if record is None:
            return None
        if owner is not None and record.claim_owner != owner:
            return None
        record.status = "PENDING"
        record.attempts = int(record.attempts or 0) + 1
        record.claim_owner = None
        record.claim_expires_at = None
        self.session.flush()
        return record
