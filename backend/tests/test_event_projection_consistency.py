from app.trading.event_projection import TradingEventProjection


def test_projection_contract_is_stable():
    event = TradingEventProjection(
        event_id="evt-001",
        event_type="ORDER_EXECUTED",
        aggregate_id="order-001",
        payload={"status": "filled"},
    )

    assert event.to_dict() == {
        "event_id": "evt-001",
        "event_type": "ORDER_EXECUTED",
        "aggregate_id": "order-001",
        "payload": {"status": "filled"},
    }
