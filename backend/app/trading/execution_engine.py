from dataclasses import dataclass
from typing import Any

from app.trading.position import Position


@dataclass
class ExecutionResult:
    success: bool
    order: Any
    message: str = ""

    @property
    def status(self) -> str:
        """Expose the order lifecycle status for legacy callers."""
        return str(getattr(self.order, "status", ""))


class TradingExecutionEngine:
    """Order -> Risk -> Broker -> Position execution pipeline."""

    def __init__(self, broker, risk_controller):
        self.broker = broker
        self.risk_controller = risk_controller
        self.positions: dict[str, Position] = {}
        self._applied_filled_volume: dict[str, float] = {}

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
            if "filled_volume" in result:
                order.filled_volume = float(result.get("filled_volume") or 0)
        elif isinstance(result, bool):
            status = "FILLED" if result else "REJECTED"
        else:
            status = str(getattr(result, "status", "SUBMITTED")).upper()
            order.broker_order = result
            order.order_id = str(getattr(result, "order_id", order.order_id or "")) or order.order_id
            if hasattr(result, "filled_volume"):
                order.filled_volume = float(getattr(result, "filled_volume") or 0)

        normalized = {
            "FINISHED": "FILLED",
            "SUCCESS": "FILLED",
            "ALIVE": "SUBMITTED",
            "PENDING": "SUBMITTED",
            "PARTIAL_FILLED": "PARTIALLY_FILLED",
            "PARTIALLYFILLED": "PARTIALLY_FILLED",
            "REJECTED": "REJECTED",
            "CANCELLED": "CANCELLED",
        }.get(status, status)
        order.status = normalized

        if normalized == "FILLED":
            if order.filled_volume <= 0:
                order.filled_volume = float(order.volume)
            self._apply_incremental_position(order)
            return ExecutionResult(True, order, "execution completed")
        if normalized == "PARTIALLY_FILLED":
            self._apply_incremental_position(order)
            return ExecutionResult(True, order, "order partially filled")
        if normalized == "REJECTED":
            return ExecutionResult(False, order, "broker rejected order")
        return ExecutionResult(True, order, "order submitted")

    def _apply_incremental_position(self, order):
        order_id = str(order.order_id or "")
        cumulative = float(getattr(order, "filled_volume", 0) or 0)
        if cumulative <= 0:
            return
        previous = self._applied_filled_volume.get(order_id, 0.0)
        delta = cumulative - previous
        if delta <= 0:
            return

        position = self.positions.get(order.symbol)
        if position is None:
            position = Position(symbol=order.symbol)
            self.positions[order.symbol] = position

        if order.side.upper() in ("BUY", "LONG"):
            position.volume += delta
        else:
            position.volume -= delta

        if order.price:
            position.avg_price = order.price
        self._applied_filled_volume[order_id] = cumulative

    def _update_position(self, order):
        """Backward-compatible full-fill position update."""
        order.filled_volume = float(order.volume)
        self._apply_incremental_position(order)
