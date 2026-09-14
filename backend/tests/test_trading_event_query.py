import asyncio

import pytest

from app.api.v1 import trading
from app.storage.orm import ORMManager
from app.trading.durable_execution_event_sink import DurableExecutionEventSink


def test_durable_projection_query_survives_sink_recreation(tmp_path, monkeypatch):
    orm = ORMManager(f"sqlite:///{tmp_path / 'projection-api.db'}")
    orm.create_tables()
    first_sink = DurableExecutionEventSink(orm.session)
    first_sink.handle("ORDER_EXECUTED", "ORDER-A", {"_event_id": "event-1", "volume": 2})
    first_sink.handle("ORDER_EXECUTED", "ORDER-A", {"_event_id": "event-2", "volume": 3})
    first_sink.handle("ORDER_EXECUTED", "ORDER-B", {"_event_id": "event-3", "volume": 5})

    recreated_sink = DurableExecutionEventSink(orm.session)
    monkeypatch.setattr(trading, "_orm", orm)
    monkeypatch.setattr(trading, "execution_event_sink", recreated_sink)

    all_events = asyncio.run(trading.list_execution_events(limit=10))
    assert [event["event_id"] for event in all_events["events"]] == [
        "event-1",
        "event-2",
        "event-3",
    ]

    filtered = asyncio.run(trading.list_execution_events(aggregate_id="ORDER-A", limit=10))
    assert filtered["events"] == [
        {
            "event_id": "event-1",
            "event_type": "ORDER_EXECUTED",
            "aggregate_id": "ORDER-A",
            "payload": {"volume": 2},
        },
        {
            "event_id": "event-2",
            "event_type": "ORDER_EXECUTED",
            "aggregate_id": "ORDER-A",
            "payload": {"volume": 3},
        },
    ]

    exact = asyncio.run(trading.list_execution_events(event_id="event-2", limit=10))
    assert [event["event_id"] for event in exact["events"]] == ["event-2"]

    with pytest.raises(Exception) as exc_info:
        asyncio.run(trading.list_execution_events(limit=0))
    assert getattr(exc_info.value, "status_code", None) == 400

    orm.engine.dispose()
