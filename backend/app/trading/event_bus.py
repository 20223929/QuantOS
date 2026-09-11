from app.trading.events import TradeEvent


class TradingEventBus:
    def __init__(self):
        self.listeners = []

    def subscribe(self, listener):
        self.listeners.append(listener)

    async def publish(self, event: TradeEvent):
        for listener in self.listeners:
            await listener(event)


trading_event_bus = TradingEventBus()
