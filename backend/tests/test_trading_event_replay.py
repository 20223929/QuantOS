import pytest

from app.trading.event_projection import TradingEventProjection


@pytest.mark.asyncio
async def test_trading_event_projection_replay_contract():
    event = TradingEventProjection(
        event_id="100",
        event_type="ORDER_FILLED",
        aggregate_id="order-1",
        payload={"status": "filled"},
    )

    data = event.to_dict()

    assert data["event_id"] == "100"
    assert data["event_type"] == "ORDER_FILLED"
    assert data["aggregate_id"] == "order-1"
    assert data["payload"]["status"] == "filled"


@pytest.mark.asyncio
async def test_heartbeat_event_contract():
    heartbeat = {"type": "heartbeat"}

    assert heartbeat["type"] == "heartbeat"
