from dataclasses import dataclass
from typing import Any

from app.trading.position import Position


@dataclass
class ExecutionResult:
    success: bool
    order: Any
    message: str = ""


class TradingExecutionEngine:
    """Order -> Risk -> Broker -> Position execution pipeline."""

    def __init__(self, broker, risk_controller):
        self.broker = broker
        self.risk_controller = risk_controller
        self.positions: dict[str, Position] = {}

    def execute(self, order):
        decision = self.risk_controller.check_order(order, self.positions.get(order.symbol, Position(order.symbol)).volume)
        if not decision.allowed:
            order.status = "REJECTED"
            order.reason = decision.reason
            return ExecutionResult(False, order, decision.reason)

        result = self.broker.submit_order(order)
        if not result:
            order.status = "REJECTED"
            order.reason = "broker rejected order"
            return ExecutionResult(False, order, order.reason)

        if isinstance(result, dict):
            order.order_id = result.get("id") or order.order_id
            order.broker_order = result.get("vendor_order")
            status = str(result.get("status", "SUBMITTED")).upper()
        else:
            status = str(getattr(result, "status", "SUBMITTED")).upper()
            order.broker_order = result
            order.order_id = str(getattr(result, "order_id", order.order_id or "")) or order.order_id

        normalized = {
            "FINISHED": "FILLED",
            "SUCCESS": "FILLED",
            "ALIVE": "SUBMITTED",
            "PENDING": "SUBMITTED",
            "REJECTED": "REJECTED",
            "CANCELLED": "CANCELLED",
        }.get(status, status)
        order.status = normalized

        if normalized == "FILLED":
            self._update_position(order)
            return ExecutionResult(True, order, "execution completed")
        if normalized == "REJECTED":
            return ExecutionResult(False, order, "broker rejected order")
        return ExecutionResult(True, order, "order submitted")

    def _update_position(self, order):
        position = self.positions.get(order.symbol)
        if position is None:
            position = Position(symbol=order.symbol)
            self.positions[order.symbol] = position

        if order.side.upper() in ("BUY", "LONG"):
            position.volume += order.volume
        else:
            position.volume -= order.volume

        if order.price:
            position.avg_price = order.price
