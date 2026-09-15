import asyncio

from app.trading.event_broadcast import TradingEventBroadcaster


def test_broadcast_delivers_event_to_subscriber():
    broadcaster = TradingEventBroadcaster()
    queue = broadcaster.subscribe()

    delivered = broadcaster.publish({"event_type": "ORDER_EXECUTED"})

    assert delivered == 1
    assert asyncio.run(queue.get()) == {"event_type": "ORDER_EXECUTED"}

    broadcaster.unsubscribe(queue)
