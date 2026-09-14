from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from app.storage.execution_outbox import ExecutionOutboxRepository


@dataclass
class ExecutionOutboxMetrics:
    delivered: int = 0
    retried: int = 0
    selected: int = 0


class ExecutionOutboxDispatcher:
    """Deliver durable execution events with per-event retry isolation."""

    def __init__(self, session_factory, handler: Callable[[str, str, dict], None], claim_seconds: int = 30):
        if claim_seconds <= 0:
            raise ValueError("claim_seconds must be positive")
        self.session_factory = session_factory
        self.handler = handler
        self.claim_seconds = claim_seconds
        self.owner = f"dispatcher-{uuid4()}"
        self.metrics = ExecutionOutboxMetrics()

    def dispatch_once(self, limit: int = 100) -> dict[str, int]:
        delivered = 0
        retried = 0

        with self.session_factory() as session:
            repository = ExecutionOutboxRepository(session)
            events = repository.claim_pending(
                limit=limit,
                owner=self.owner,
                claim_seconds=self.claim_seconds,
            )

            for event in events:
                try:
                    self.handler(event.event_type, event.aggregate_id, json.loads(event.payload))
                except Exception:
                    if repository.mark_retry(event.event_id, owner=self.owner) is not None:
                        retried += 1
                else:
                    if repository.mark_processed(event.event_id, owner=self.owner) is not None:
                        delivered += 1

            session.commit()

        self.metrics.delivered += delivered
        self.metrics.retried += retried
        self.metrics.selected += len(events)
        return {"delivered": delivered, "retried": retried, "selected": len(events)}

    def snapshot(self) -> dict[str, int]:
        return {
            "delivered": self.metrics.delivered,
            "retried": self.metrics.retried,
            "selected": self.metrics.selected,
        }
