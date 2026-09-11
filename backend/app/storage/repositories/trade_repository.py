from backend.app.storage.models.trade import TradeRecord
from .base_repository import BaseRepository


class TradeRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session)
        self.model = TradeRecord

    def save_trade(self, trade: TradeRecord):
        return self.save(trade)
