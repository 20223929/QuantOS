"""Trading state projection foundation.

Maintains current trading state derived from execution events.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderStateProjection:
    order_id: str
    status: str
    version: int = 0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PositionStateProjection:
    position_id: str
    quantity: float
    version: int = 0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TradingStateProjection:
    last_event_id: str | None = None
    state_version: int = 0
    orders: dict[str, OrderStateProjection] = field(default_factory=dict)
    positions: dict[str, PositionStateProjection] = field(default_factory=dict)

    def apply_event(self, event: dict[str, Any]) -> bool:
        """Apply event once and advance state version."""
        event_id = event.get("event_id")
        if event_id == self.last_event_id:
            return False

        self.last_event_id = event_id
        self.state_version += 1

        event_type = event.get("event_type")
        payload = event.get("payload", {})

        if event_type in {"ORDER_SUBMITTED", "ORDER_FILLED", "ORDER_CANCELLED"}:
            order_id = event.get("aggregate_id")
            self.orders[order_id] = OrderStateProjection(
                order_id=order_id,
                status=event_type,
                version=self.state_version,
                data=payload,
            )

        return True

    def snapshot(self) -> dict[str, Any]:
        return {
            "last_event_id": self.last_event_id,
            "state_version": self.state_version,
            "orders": {k: vars(v) for k, v in self.orders.items()},
            "positions": {k: vars(v) for k, v in self.positions.items()},
        }
