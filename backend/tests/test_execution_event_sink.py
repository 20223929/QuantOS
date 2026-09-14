import pytest

from app.trading.execution_event_sink import ExecutionEventSink


def test_sink_accepts_supported_execution_event():
    sink = ExecutionEventSink()

    sink.handle("ORDER_EXECUTED", "O-SINK-001", {"status": "FILLED"})

    assert sink.snapshot() == [
        {
            "event_type": "ORDER_EXECUTED",
            "aggregate_id": "O-SINK-001",
            "payload": {"status": "FILLED"},
        }
    ]


def test_sink_rejects_unknown_event_type():
    sink = ExecutionEventSink()

    with pytest.raises(ValueError, match="unsupported execution event type"):
        sink.handle("UNKNOWN", "O-SINK-002", {})


def test_sink_snapshot_is_not_mutable_from_caller():
    sink = ExecutionEventSink(max_events=2)
    payload = {"nested": {"status": "FILLED"}}

    sink.handle("ORDER_EXECUTED", "O-SINK-003", payload)
    snapshot = sink.snapshot()
    snapshot[0]["payload"]["nested"]["status"] = "CHANGED"
    payload["nested"]["status"] = "MUTATED"

    assert sink.snapshot()[0]["payload"]["nested"]["status"] == "FILLED"


def test_sink_keeps_only_latest_bounded_events():
    sink = ExecutionEventSink(max_events=2)

    for index in range(3):
        sink.handle("ORDER_EXECUTED", f"O-SINK-{index}", {"index": index})

    assert [event["aggregate_id"] for event in sink.snapshot()] == [
        "O-SINK-1",
        "O-SINK-2",
    ]


def test_sink_deduplicates_replayed_execution_event():
    sink = ExecutionEventSink()

    sink.handle("ORDER_EXECUTED", "O-SINK-DUP", {"status": "FILLED", "attempt": 1})
    sink.handle("ORDER_EXECUTED", "O-SINK-DUP", {"status": "FILLED", "attempt": 2})

    assert sink.snapshot() == [
        {
            "event_type": "ORDER_EXECUTED",
            "aggregate_id": "O-SINK-DUP",
            "payload": {"status": "FILLED", "attempt": 1},
        }
    ]


def test_sink_uses_event_id_for_same_order_lifecycle_events():
    sink = ExecutionEventSink()

    sink.handle("ORDER_EXECUTED", "O-SINK-PARTIAL", {"event_id": "fill-1", "volume": 2})
    sink.handle("ORDER_EXECUTED", "O-SINK-PARTIAL", {"event_id": "fill-2", "volume": 3})
    sink.handle("ORDER_EXECUTED", "O-SINK-PARTIAL", {"event_id": "fill-2", "volume": 999})

    assert sink.snapshot() == [
        {
            "event_type": "ORDER_EXECUTED",
            "aggregate_id": "O-SINK-PARTIAL",
            "payload": {"event_id": "fill-1", "volume": 2},
        },
        {
            "event_type": "ORDER_EXECUTED",
            "aggregate_id": "O-SINK-PARTIAL",
            "payload": {"event_id": "fill-2", "volume": 3},
        },
    ]


def test_sink_allows_reuse_of_evicted_event_key():
    sink = ExecutionEventSink(max_events=1)

    sink.handle("ORDER_EXECUTED", "O-SINK-A", {"index": 1})
    sink.handle("ORDER_EXECUTED", "O-SINK-B", {"index": 2})
    sink.handle("ORDER_EXECUTED", "O-SINK-A", {"index": 3})

    assert [event["aggregate_id"] for event in sink.snapshot()] == ["O-SINK-A"]
    assert sink.snapshot()[0]["payload"] == {"index": 3}


def test_durable_sink_deduplicates_same_event_id_across_sink_instances(tmp_path):
    from app.trading.durable_execution_event_sink import DurableExecutionEventSink
    from app.storage.models.base import Base
    from app.storage.models.consumption import ConsumedExecutionEventModel
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{tmp_path / 'consumer.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, future=True)

    first = DurableExecutionEventSink(session_factory)
    second = DurableExecutionEventSink(session_factory)
    first.handle("ORDER_EXECUTED", "O-DURABLE", {"_event_id": "durable-1", "volume": 2})
    second.handle("ORDER_EXECUTED", "O-DURABLE", {"_event_id": "durable-1", "volume": 999})

    assert first.snapshot()[0]["payload"] == {"volume": 2}
    assert second.snapshot() == []
    with session_factory() as session:
        assert session.scalar(select(func.count(ConsumedExecutionEventModel.id))) == 1
