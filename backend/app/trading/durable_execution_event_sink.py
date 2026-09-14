from __future__ import annotations

from copy import deepcopy

from app.storage.consumed_events import ConsumedExecutionEventRepository


class DurableExecutionEventSink:
    """Execution event sink with database-backed event-idempotency."""

    SUPPORTED_EVENT_TYPES = {"ORDER_EXECUTED"}

    def __init__(self, session_factory, max_events: int = 1000):
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        self.session_factory = session_factory
        self.max_events = max_events
        self._events: list[dict] = []

    def handle(self, event_type: str, aggregate_id: str, payload: dict) -> None:
        if event_type not in self.SUPPORTED_EVENT_TYPES:
            raise ValueError(f"unsupported execution event type: {event_type}")
        if not aggregate_id:
            raise ValueError("aggregate_id is required")

        event_id = str(payload.get("_event_id", "") or payload.get("event_id", "") or "")
        if not event_id:
            raise ValueError("event_id is required for durable execution events")

        with self.session_factory() as session:
            repository = ConsumedExecutionEventRepository(session)
            consumed = repository.mark_consumed(event_id, event_type, aggregate_id)
            session.commit()

        if not consumed:
            return

        stored_payload = deepcopy(payload)
        stored_payload.pop("_event_id", None)
        self._events.append(
            {
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "payload": stored_payload,
            }
        )
        if len(self._events) > self.max_events:
            del self._events[: len(self._events) - self.max_events]

    def snapshot(self) -> list[dict]:
        return deepcopy(self._events)
