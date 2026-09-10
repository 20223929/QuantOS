class OrderManager:
    def __init__(self):
        self.orders = []

    async def submit(self, order):
        self.orders.append(order)
        return order

    async def cancel(self, order_id):
        return {"order_id": order_id, "status": "cancelled"}
