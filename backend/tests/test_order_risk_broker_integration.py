from app.risk.controller import RiskController
from app.risk.limit import RiskLimit
from app.trading.order_manager import OrderManager


class MockBroker:
    def __init__(self):
        self.submitted = []

    def submit_order(self, order):
        order.status = "SUBMITTED"
        self.submitted.append(order)
        return order

    def cancel_order(self, order):
        order.status = "CANCELLED"
        return order


def test_order_manager_risk_broker_flow():
    broker = MockBroker()
    risk = RiskController(RiskLimit(max_position=1))
    manager = OrderManager(broker, risk)

    order = manager.create_order("SHFE.rb", "BUY", 1)
    result = manager.submit(order)

    assert result.status == "SUBMITTED"
    assert len(broker.submitted) == 1


def test_order_manager_rejects_risk_failed_order():
    broker = MockBroker()
    risk = RiskController(RiskLimit(max_position=1))
    manager = OrderManager(broker, risk)

    order = manager.create_order("SHFE.rb", "BUY", 2)
    result = manager.submit(order)

    assert result.status == "REJECTED"
    assert len(broker.submitted) == 0
