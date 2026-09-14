from __future__ import annotations

from copy import deepcopy


class ExecutionEventSink:
    """Application boundary for consumed execution events."""

    SUPPORTED_EVENT_TYPES = {"ORDER_EXECUTED"}

    def __init__(self, max_events: int = 1000):
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        self.max_events = max_events
        self._events: list[dict] = []

    def handle(self, event_type: str, aggregate_id: str, payload: dict) -> None:
        if event_type not in self.SUPPORTED_EVENT_TYPES:
            raise ValueError(f"unsupported execution event type: {event_type}")
        if not aggregate_id:
            raise ValueError("aggregate_id is required")
        self._events.append(
            {
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "payload": deepcopy(payload),
            }
        )
        if len(self._events) > self.max_events:
            del self._events[:-self.max_events]

    def snapshot(self) -> list[dict]:
        return deepcopy(self._events)
