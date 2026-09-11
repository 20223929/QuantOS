from backend.app.storage.event_persistence import EventPersistenceHandler


class DummyRepo:
    def __init__(self):
        self.value = None

    def save(self, value):
        self.value = value
        return value


class Event:
    def __init__(self, data):
        self.data = data


class PositionEvent(Event):
    pass


class MarketDataEvent(Event):
    pass


def test_position_and_market_event_persistence():
    position = DummyRepo()
    market = DummyRepo()
    handler = EventPersistenceHandler({"position": position, "market": market})

    handler.handle(PositionEvent("position"))
    handler.handle(MarketDataEvent("market"))

    assert position.value == "position"
    assert market.value == "market"
