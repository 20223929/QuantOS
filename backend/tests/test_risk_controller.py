from app.risk.controller import RiskController
from app.risk.limit import RiskLimit


class Order:
    def __init__(self, volume):
        self.volume = volume


def test_risk_controller_accepts_valid_order():
    controller = RiskController(RiskLimit(max_position=2))
    result = controller.check_order(Order(1))
    assert result.allowed is True


def test_risk_controller_rejects_exceed_position():
    controller = RiskController(RiskLimit(max_position=1))
    result = controller.check_order(Order(2))
    assert result.allowed is False
