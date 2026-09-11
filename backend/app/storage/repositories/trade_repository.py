from backend.app.storage.models.trade import TradeRecord


class TradeRepository:
    def __init__(self):
        self.items = []

    def save(self, trade: TradeRecord):
        self.items.append(trade)
        return trade

    def all(self):
        return self.items
