from app.risk.controller import RiskController
from app.risk.limit import RiskLimit
from app.trading.order_manager import OrderManager


class MockBroker:
    def __init__(self, status="ALIVE"):
        self.submitted = []
        self.status = status

    def submit_order(self, order):
        self.submitted.append(order)
        return {"id": "T001", "status": self.status}

    def cancel_order(self, order):
        return {"id": "T001", "status": "CANCELLED"}


def test_order_manager_risk_broker_flow():
    broker = MockBroker("ALIVE")
    risk = RiskController(RiskLimit(max_position=1))
    manager = OrderManager(broker, risk)

    order = manager.create_order("SHFE.rb", "BUY", 1)
    result = manager.submit(order)

    assert result.success is True
    assert result.order.status == "SUBMITTED"
    assert len(broker.submitted) == 1


def test_order_manager_rejects_risk_failed_order():
    broker = MockBroker("ALIVE")
    risk = RiskController(RiskLimit(max_position=1))
    manager = OrderManager(broker, risk)

    order = manager.create_order("SHFE.rb", "BUY", 2)
    result = manager.submit(order)

    assert result.success is False
    assert result.order.status == "REJECTED"
    assert len(broker.submitted) == 0


def test_filled_order_updates_execution_position():
    broker = MockBroker("FINISHED")
    risk = RiskController(RiskLimit(max_position=2))
    manager = OrderManager(broker, risk)

    order = manager.create_order("SHFE.rb", "BUY", 1, 3500)
    result = manager.submit(order)

    assert result.success is True
    assert result.order.status == "FILLED"
    assert manager.execution_engine.positions["SHFE.rb"].volume == 1
