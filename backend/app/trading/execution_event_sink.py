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
        self._event_keys: set[tuple[str, str]] = set()

    def handle(self, event_type: str, aggregate_id: str, payload: dict) -> None:
        if event_type not in self.SUPPORTED_EVENT_TYPES:
            raise ValueError(f"unsupported execution event type: {event_type}")
        if not aggregate_id:
            raise ValueError("aggregate_id is required")

        key = (event_type, str(aggregate_id))
        if key in self._event_keys:
            return

        self._events.append(
            {
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "payload": deepcopy(payload),
            }
        )
        self._event_keys.add(key)
        if len(self._events) > self.max_events:
            removed = self._events[:-self.max_events]
            del self._events[:-self.max_events]
            self._event_keys.difference_update(
                (item["event_type"], str(item["aggregate_id"])) for item in removed
            )

    def snapshot(self) -> list[dict]:
        return deepcopy(self._events)
