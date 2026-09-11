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

    def check_order(self, order: Any) -> RiskDecision:
        volume = getattr(order, "volume", 0)
        if not self.limit.allow_position(volume):
            return RiskDecision(False, "position limit exceeded")

        return RiskDecision(True, "risk check passed")
