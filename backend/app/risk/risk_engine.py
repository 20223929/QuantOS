from dataclasses import dataclass


@dataclass
class RiskResult:
    allowed: bool
    reason: str = ""


class RiskEngine:
    """Central risk control gateway before order submission."""

    def __init__(self):
        self.enabled = True

    def check_order(self, order) -> RiskResult:
        if not self.enabled:
            return RiskResult(False, "risk engine disabled")
        return RiskResult(True, "passed")

    def stop_all(self):
        self.enabled = False

    def resume(self):
        self.enabled = True
