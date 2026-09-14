from app.risk.controller import RiskController
from app.risk.limit import RiskLimit
from app.trading.execution_engine import TradingExecutionEngine
from app.trading.order import Order


class MockBroker:
    def __init__(self):
        self.orders = []

    def submit_order(self, order):
        self.orders.append(order)
        return True


class PartialBroker:
    def __init__(self):
        self.orders = []
        self.filled_volume = 2

    def submit_order(self, order):
        self.orders.append(order)
        return {
            "id": order.order_id or "O-PARTIAL-RESUME",
            "status": "PARTIALLY_FILLED",
            "filled_volume": self.filled_volume,
        }


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


def test_execution_restores_persisted_fill_cache_before_replayed_partial_fill():
    broker = PartialBroker()
    risk = RiskController(RiskLimit(max_position=10))
    engine = TradingExecutionEngine(broker, risk)
    engine.restore_filled_volumes({"O-PARTIAL-RESUME": 2})
    engine.positions["IF"] = __import__("app.trading.position", fromlist=["Position"]).Position(
        symbol="IF", volume=2
    )

    order = Order(
        symbol="IF",
        side="BUY",
        volume=5,
        price=3000,
        order_id="O-PARTIAL-RESUME",
        filled_volume=2,
    )
    result = engine.execute(order)

    assert result.success
    assert order.status == "PARTIALLY_FILLED"
    assert order.filled_volume == 2
    assert engine.positions["IF"].volume == 2
    assert len(broker.orders) == 1
