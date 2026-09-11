from app.trading.execution_engine import TradingExecutionEngine
from app.trading.order import Order
from app.risk.controller import RiskController
from app.risk.limit import RiskLimit


class MockBroker:
    def __init__(self):
        self.orders = []

    def submit_order(self, order):
        self.orders.append(order)
        return True


def test_execution_updates_position():
    broker = MockBroker()
    risk = RiskController(RiskLimit(max_position=10))
    engine = TradingExecutionEngine(broker, risk)

    order = Order(symbol="IF", side="BUY", volume=2, price=3000)
    result = engine.execute(order)

    assert result.success
    assert engine.positions["IF"].volume == 2
    assert len(broker.orders) == 1


def test_execution_rejects_risk_limit():
    broker = MockBroker()
    risk = RiskController(RiskLimit(max_position=1))
    engine = TradingExecutionEngine(broker, risk)

    order = Order(symbol="IF", side="BUY", volume=2, price=3000)
    result = engine.execute(order)

    assert not result.success
    assert order.status == "REJECTED"
    assert len(broker.orders) == 0
