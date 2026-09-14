from app.risk.controller import RiskController
from app.risk.limit import RiskLimit


class Order:
    def __init__(self, volume, side="BUY"):
        self.volume = volume
        self.side = side


def test_risk_controller_accepts_valid_order():
    controller = RiskController(RiskLimit(max_position=2))
    result = controller.check_order(Order(1), current_position=1)
    assert result.allowed is True
    assert result.projected_position == 2


def test_risk_controller_rejects_exceed_position():
    controller = RiskController(RiskLimit(max_position=1))
    result = controller.check_order(Order(1), current_position=1)
    assert result.allowed is False
    assert result.projected_position == 2


def test_sell_reduces_projected_position():
    controller = RiskController(RiskLimit(max_position=1))
    result = controller.check_order(Order(1, "SELL"), current_position=1)
    assert result.allowed is True
    assert result.projected_position == 0


def test_risk_controller_rejects_drawdown():
    controller = RiskController(RiskLimit(max_drawdown=0.1))
    result = controller.check_drawdown(0.2)
    assert result.allowed is False
