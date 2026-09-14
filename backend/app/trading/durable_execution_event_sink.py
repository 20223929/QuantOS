from __future__ import annotations

from copy import deepcopy
import json

from app.storage.consumed_events import ConsumedExecutionEventRepository
from app.storage.execution_projection import ExecutionEventProjectionRepository


class DurableExecutionEventSink:
    """Execution event sink with atomic inbox/projection persistence."""

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

        stored_payload = deepcopy(payload)
        stored_payload.pop("_event_id", None)
        with self.session_factory() as session:
            consumed = ConsumedExecutionEventRepository(session).mark_consumed(
                event_id, event_type, aggregate_id
            )
            if not consumed:
                session.rollback()
                return
            ExecutionEventProjectionRepository(session).save(
                event_id, event_type, aggregate_id, stored_payload
            )
            session.commit()

        self._events.append(self._serialize_event(event_id, event_type, aggregate_id, stored_payload))
        if len(self._events) > self.max_events:
            del self._events[: len(self._events) - self.max_events]

    @staticmethod
    def _serialize_event(event_id: str, event_type: str, aggregate_id: str, payload: dict) -> dict:
        return {
            "event_id": event_id,
            "event_type": event_type,
            "aggregate_id": aggregate_id,
            "payload": json.loads(json.dumps(payload, ensure_ascii=False)),
        }

    def snapshot(self) -> list[dict]:
        return deepcopy(self._events)

    def durable_snapshot(
        self,
        *,
        event_type: str | None = None,
        aggregate_id: str | None = None,
        event_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        effective_limit = self.max_events if limit is None else limit
        with self.session_factory() as session:
            rows = ExecutionEventProjectionRepository(session).list_events(
                event_type=event_type,
                aggregate_id=aggregate_id,
                event_id=event_id,
                limit=effective_limit,
            )
            return [
                self._serialize_event(
                    row.event_id,
                    row.event_type,
                    row.aggregate_id,
                    json.loads(row.payload),
                )
                for row in rows
            ]
