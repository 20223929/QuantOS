from app.trading.events import OrderEvent, TradeEvent


def test_order_event_create():
    event = OrderEvent(order_id="1", status="FILLED")
    assert event.status == "FILLED"


def test_trade_event_create():
    event = TradeEvent(
        order_id="1",
        symbol="SHFE.rb",
        volume=1,
        price=3500,
    )
    assert event.symbol == "SHFE.rb"
