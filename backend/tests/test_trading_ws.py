from app.trading.event_bus import TradingEventBus


def test_event_bus_subscribe():
    bus = TradingEventBus()

    async def handler(event):
        return event

    bus.subscribe(handler)

    assert len(bus.listeners) == 1
