"""In-memory paper trading broker for development and regression tests."""

from typing import Any, Dict
from uuid import uuid4


class PaperBroker:
    """Deterministic broker that fills orders immediately."""

    def __init__(self):
        self.orders: Dict[str, dict] = {}
        self.positions: Dict[str, float] = {}

    @staticmethod
    def _order_id(order: Any) -> str:
        return str(getattr(order, "order_id", None) or getattr(order, "id", None) or "")

    def submit_order(self, order: Any) -> dict:
        order_id = self._order_id(order) or uuid4().hex
        filled_order = {
            "id": order_id,
            "symbol": order.symbol,
            "side": str(order.side).upper(),
            "volume": int(order.volume),
            "price": float(getattr(order, "price", 0.0) or 0.0),
            "offset": str(getattr(order, "offset", "OPEN")).upper(),
            "status": "FILLED",
        }
        self.orders[order_id] = filled_order
        order.order_id = order_id

        symbol = order.symbol
        volume = int(order.volume)
        side = str(order.side).upper()
        if side in {"SELL", "SHORT"}:
            self.positions[symbol] = self.positions.get(symbol, 0) - volume
        else:
            self.positions[symbol] = self.positions.get(symbol, 0) + volume

        return filled_order

    def cancel_order(self, order: Any) -> dict:
        order_id = self._order_id(order) if not isinstance(order, str) else order
        stored = self.orders.get(order_id)
        if stored and stored["status"] == "FILLED":
            return {"id": order_id, "status": "NOT_CANCELLABLE"}
        if stored:
            stored["status"] = "CANCELLED"
            return stored
        return {"id": order_id, "status": "NOT_FOUND"}

    def query_position(self) -> Dict[str, float]:
        return dict(self.positions)

    def query_orders(self) -> Dict[str, dict]:
        return dict(self.orders)
