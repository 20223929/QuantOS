from dataclasses import dataclass
from typing import Any

from .limit import RiskLimit


@dataclass
class RiskDecision:
    allowed: bool
    reason: str = ""


class RiskController:
    """Risk validation layer between order flow and execution."""

    def __init__(self, limit: RiskLimit | None = None):
        self.limit = limit or RiskLimit()

    def check_order(self, order: Any, current_position: int = 0) -> RiskDecision:
        volume = getattr(order, "volume", 0)
        total_position = current_position + volume

        if not self.limit.allow_position(total_position):
            return RiskDecision(False, "position limit exceeded")

        return RiskDecision(True, "risk check passed")

    def check_drawdown(self, drawdown: float) -> RiskDecision:
        max_drawdown = getattr(self.limit, "max_drawdown", 1.0)
        if drawdown > max_drawdown:
            return RiskDecision(False, "drawdown limit exceeded")

        return RiskDecision(True, "drawdown check passed")
