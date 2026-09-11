from app.trading.order_manager import OrderManager


class MockBroker:
    def submit_order(self, order):
        order.status = "FILLED"
        return order

    def cancel_order(self, order):
        order.status = "CANCELLED"
        return order


def test_order_manager_submit():
    manager = OrderManager(MockBroker())
    order = manager.create_order("SHFE.rb", "BUY", 1)
    result = manager.submit(order)
    assert result.status == "FILLED"


def test_order_manager_cancel():
    manager = OrderManager(MockBroker())
    order = manager.create_order("SHFE.rb", "BUY", 1)
    result = manager.cancel(order)
    assert result.status == "CANCELLED"
