from backend.app.storage.models.order import OrderRecord


class OrderRepository:
    def __init__(self):
        self.items = []

    def save(self, order: OrderRecord):
        self.items.append(order)
        return order

    def all(self):
        return self.items
