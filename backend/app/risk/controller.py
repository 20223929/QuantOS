from dataclasses import dataclass
from typing import Any

from .limit import RiskLimit


@dataclass
class RiskDecision:
    allowed: bool
    reason: str = ""
    projected_position: int = 0


class RiskController:
    """Risk validation layer between order flow and execution."""

    def __init__(self, limit: RiskLimit | None = None):
        self.limit = limit or RiskLimit()

    @staticmethod
    def projected_position(order: Any, current_position: int = 0) -> int:
        volume = int(getattr(order, "volume", 0) or 0)
        side = str(getattr(order, "side", "BUY")).upper()
        return current_position + volume if side in {"BUY", "LONG"} else current_position - volume

    def check_order(self, order: Any, current_position: int = 0) -> RiskDecision:
        projected = self.projected_position(order, current_position)
        if not self.limit.allow_position(abs(projected)):
            return RiskDecision(False, "position limit exceeded", projected)
        return RiskDecision(True, "risk check passed", projected)

    def check_drawdown(self, drawdown: float) -> RiskDecision:
        max_drawdown = getattr(self.limit, "max_drawdown", 1.0)
        if drawdown > max_drawdown:
            return RiskDecision(False, "drawdown limit exceeded", 0)
        return RiskDecision(True, "drawdown check passed", 0)
