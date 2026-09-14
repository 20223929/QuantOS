from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from app.storage.execution_outbox import ExecutionOutboxRepository


@dataclass
class ExecutionOutboxMetrics:
    delivered: int = 0
    retried: int = 0
    selected: int = 0


class ExecutionOutboxDispatcher:
    """Deliver durable execution events with per-event retry isolation."""

    def __init__(self, session_factory, handler: Callable[[str, str, dict], None]):
        self.session_factory = session_factory
        self.handler = handler
        self.metrics = ExecutionOutboxMetrics()

    def dispatch_once(self, limit: int = 100) -> dict[str, int]:
        delivered = 0
        retried = 0

        with self.session_factory() as session:
            repository = ExecutionOutboxRepository(session)
            events = repository.pending(limit)

            for event in events:
                try:
                    self.handler(event.event_type, event.aggregate_id, json.loads(event.payload))
                except Exception:
                    repository.mark_retry(event.event_id)
                    retried += 1
                else:
                    repository.mark_processed(event.event_id)
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
