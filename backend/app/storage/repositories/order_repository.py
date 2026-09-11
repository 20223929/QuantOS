from backend.app.storage.models.order import OrderRecord
from .base_repository import BaseRepository


class OrderRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session)
        self.model = OrderRecord

    def save_order(self, order: OrderRecord):
        return self.save(order)
