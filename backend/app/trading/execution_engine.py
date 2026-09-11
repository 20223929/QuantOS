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
        self.positions = {}

    def execute(self, order):
        decision = self.risk_controller.check_order(order)
        if not decision.allowed:
            order.status = "REJECTED"
            return ExecutionResult(False, order, decision.reason)

        result = self.broker.submit_order(order)
        if result:
            order.status = "FILLED"
            self._update_position(order)
            return ExecutionResult(True, order, "execution completed")

        return ExecutionResult(False, order, "broker rejected order")

    def _update_position(self, order):
        position = self.positions.get(order.symbol)
        if position is None:
            position = Position(symbol=order.symbol)
            self.positions[order.symbol] = position

        if order.side.upper() in ("BUY", "LONG"):
            position.volume += order.volume
        else:
            position.volume -= order.volume

        position.avg_price = order.price or position.avg_price
