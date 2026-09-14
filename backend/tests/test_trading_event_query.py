from fastapi import FastAPI
from fastapi.testclient import TestClient

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

    api = FastAPI()
    api.include_router(trading.router, prefix="/api/v1")

    with TestClient(api) as client:
        all_events = client.get("/api/v1/trading/events", params={"limit": 10})
        assert all_events.status_code == 200
        assert [event["event_id"] for event in all_events.json()["events"]] == [
            "event-1",
            "event-2",
            "event-3",
        ]

        filtered = client.get(
            "/api/v1/trading/events",
            params={"aggregate_id": "ORDER-A", "limit": 10},
        )
        assert filtered.status_code == 200
        assert filtered.json()["events"] == [
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

        exact = client.get(
            "/api/v1/trading/events",
            params={"event_id": "event-2", "limit": 10},
        )
        assert exact.status_code == 200
        assert [event["event_id"] for event in exact.json()["events"]] == ["event-2"]

        invalid_limit = client.get("/api/v1/trading/events", params={"limit": 0})
        assert invalid_limit.status_code == 400

    orm.engine.dispose()
