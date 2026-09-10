"""Paper trading broker implementation."""

from typing import Dict


class PaperBroker:
    """Simple in-memory broker for simulation and tests."""

    def __init__(self):
        self.orders: Dict[str, dict] = {}
        self.positions: Dict[str, float] = {}

    def submit_order(self, order: dict) -> dict:
        order_id = order.get("id", str(len(self.orders) + 1))
        filled_order = {
            **order,
            "id": order_id,
            "status": "FILLED",
        }
        self.orders[order_id] = filled_order

        symbol = order["symbol"]
        volume = order.get("volume", 0)
        side = order.get("side", "BUY")

        if side == "SELL":
            self.positions[symbol] = self.positions.get(symbol, 0) - volume
        else:
            self.positions[symbol] = self.positions.get(symbol, 0) + volume

        return filled_order

    def cancel_order(self, order_id: str) -> dict:
        order = self.orders.get(order_id)
        if order:
            order["status"] = "CANCELLED"
        return order or {"id": order_id, "status": "NOT_FOUND"}

    def query_position(self) -> Dict[str, float]:
        return self.positions
