from app.trading.order import Order


class OrderManager:
    """Coordinate order lifecycle between strategy, risk and broker."""

    def __init__(self, broker, risk_controller=None):
        self.broker = broker
        self.risk_controller = risk_controller
        self.orders = {}

    def create_order(self, symbol: str, side: str, volume: int, price: float | None = None) -> Order:
        order = Order(
            symbol=symbol,
            side=side,
            volume=volume,
            price=price,
        )
        self.orders[id(order)] = order
        return order

    def submit(self, order: Order):
        if self.risk_controller:
            decision = self.risk_controller.check_order(order)
            if not decision.allowed:
                order.status = "REJECTED"
                return order

        return self.broker.submit_order(order)

    def cancel(self, order):
        return self.broker.cancel_order(order)
