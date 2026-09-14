from __future__ import annotations

from app.risk.controller import RiskController
from app.risk.limit import RiskLimit
from app.trading.execution_engine import TradingExecutionEngine
from app.trading.order import Order


class OrderManager:
    """Coordinate order creation, risk validation and broker execution."""

    def __init__(self, broker, risk_controller=None):
        # Keep the historical one-argument constructor compatible while allowing
        # production callers to inject the platform risk controller explicitly.
        if risk_controller is None:
            risk_controller = RiskController(RiskLimit())
        self.execution_engine = TradingExecutionEngine(broker, risk_controller)
        self.orders: dict[str, Order] = {}

    def create_order(self, symbol: str, side: str, volume: int, price: float | None = None, offset: str = "OPEN") -> Order:
        order = Order(symbol=symbol, side=side.upper(), volume=volume, price=price or 0.0, offset=offset.upper())
        return order

    def submit(self, order: Order):
        result = self.execution_engine.execute(order)
        if order.order_id:
            self.orders[order.order_id] = order
        return result

    def cancel(self, order: Order):
        broker_order = order.broker_order or order.order_id or order
        result = self.execution_engine.broker.cancel_order(broker_order)
        if isinstance(result, dict):
            order.status = str(result.get("status", order.status)).upper()
        elif result is not None:
            order.status = str(getattr(result, "status", order.status)).upper()
        return result

    def get(self, order_id: str):
        return self.orders.get(order_id)
