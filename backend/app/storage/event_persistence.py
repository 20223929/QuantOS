class EventPersistenceHandler:
    def __init__(self, repositories):
        self.repositories = repositories

    def handle(self, event):
        name = event.__class__.__name__

        if name == "OrderEvent" and "order" in self.repositories:
            return self.repositories["order"].save(event.data)

        if name == "TradeEvent" and "trade" in self.repositories:
            return self.repositories["trade"].save(event.data)

        if name == "PositionEvent" and "position" in self.repositories:
            return self.repositories["position"].save(event.data)

        if name == "MarketDataEvent" and "market" in self.repositories:
            return self.repositories["market"].save(event.data)

        return None
