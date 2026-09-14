from __future__ import annotations

import json
from collections.abc import Callable

from app.storage.execution_outbox import ExecutionOutboxRepository


class ExecutionOutboxDispatcher:
    """Deliver durable execution events with per-event retry isolation."""

    def __init__(self, session_factory, handler: Callable[[str, str, dict], None]):
        self.session_factory = session_factory
        self.handler = handler

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

        return {"delivered": delivered, "retried": retried, "selected": len(events)}
