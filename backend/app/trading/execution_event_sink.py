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
        self._stored_keys: list[tuple[str, str]] = []

    def handle(self, event_type: str, aggregate_id: str, payload: dict) -> None:
        if event_type not in self.SUPPORTED_EVENT_TYPES:
            raise ValueError(f"unsupported execution event type: {event_type}")
        if not aggregate_id:
            raise ValueError("aggregate_id is required")

        event_id = str(payload.get("_event_id", "") or "")
        key = (event_type, event_id) if event_id else (event_type, str(aggregate_id))
        if key in self._event_keys:
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
        self._event_keys.add(key)
        self._stored_keys.append(key)
        if len(self._events) > self.max_events:
            removed_count = len(self._events) - self.max_events
            del self._events[:removed_count]
            removed_keys = self._stored_keys[:removed_count]
            del self._stored_keys[:removed_count]
            self._event_keys.difference_update(removed_keys)

    def snapshot(self) -> list[dict]:
        return deepcopy(self._events)
