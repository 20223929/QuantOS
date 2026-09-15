"""Coordinator between event projections and trading state snapshots."""

from typing import Any

from app.trading.state_projection import TradingStateProjection


class TradingStateProjector:
    """Apply projected trading events into a consistent state snapshot."""

    def __init__(self, state: TradingStateProjection | None = None):
        self.state = state or TradingStateProjection()

    def apply(self, event: dict[str, Any]) -> bool:
        """Apply a projected event and return whether state changed."""
        event_id = event.get("event_id")
        if event_id and event_id == self.state.last_event_id:
            return False

        self.state.apply_event(event)
        return True

    def snapshot(self) -> dict[str, Any]:
        return self.state.snapshot()
