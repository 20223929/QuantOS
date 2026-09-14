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
