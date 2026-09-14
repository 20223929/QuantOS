from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.execution_outbox_dispatcher import ExecutionOutboxDispatcher
from app.storage.execution_projection import ExecutionEventProjectionRepository
from app.storage.models.base import Base
from app.storage.models.consumption import ConsumedExecutionEventModel
from app.storage.models.execution_projection import ExecutionEventProjectionModel
from app.storage.models.outbox import ExecutionOutboxModel
from app.trading.durable_execution_event_sink import DurableExecutionEventSink


def _file_session_factory(path):
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_durable_consumer_deduplicates_concurrent_replay_across_instances(tmp_path):
    session_factory = _file_session_factory(tmp_path / "durable-consumer.db")
    first = DurableExecutionEventSink(session_factory)
    second = DurableExecutionEventSink(session_factory)

    first.handle("ORDER_EXECUTED", "O-DURABLE-CONCURRENT", {"_event_id": "durable-concurrent", "volume": 2})
    second.handle("ORDER_EXECUTED", "O-DURABLE-CONCURRENT", {"_event_id": "durable-concurrent", "volume": 999})

    assert first.snapshot() == [{"event_type": "ORDER_EXECUTED", "aggregate_id": "O-DURABLE-CONCURRENT", "payload": {"volume": 2}}]
    assert second.snapshot() == []
    with session_factory() as session:
        assert session.scalar(select(func.count(ConsumedExecutionEventModel.id))) == 1
        assert session.scalar(select(func.count(ExecutionEventProjectionModel.id))) == 1


def test_claim_loss_replay_is_deduplicated_by_durable_consumer(tmp_path):
    session_factory_a = _file_session_factory(tmp_path / "claim-loss-durable.db")
    session_factory_b = _file_session_factory(tmp_path / "claim-loss-durable.db")
    with session_factory_a() as session:
        ExecutionOutboxRepository(session).enqueue("ORDER_EXECUTED", "O-CLAIM-DURABLE", {"order_id": "O-CLAIM-DURABLE", "volume": 5}, event_id="durable-claim-loss")
        session.commit()

    first_sink = DurableExecutionEventSink(session_factory_a)
    second_sink = DurableExecutionEventSink(session_factory_b)

    def handler(event_type, aggregate_id, payload):
        first_sink.handle(event_type, aggregate_id, payload)
        with session_factory_b() as session:
            event = session.scalar(select(ExecutionOutboxModel).where(ExecutionOutboxModel.event_id == "durable-claim-loss"))
            event.status = "PENDING"
            event.claim_owner = "reclaimer"
            event.claim_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            session.commit()

    dispatcher_a = ExecutionOutboxDispatcher(session_factory_a, handler, claim_seconds=30)
    result_a = dispatcher_a.dispatch_once()
    assert result_a == {"delivered": 0, "retried": 0, "selected": 1}
    assert dispatcher_a.snapshot()["claim_lost"] == 1

    dispatcher_b = ExecutionOutboxDispatcher(
        session_factory_b,
        lambda event_type, aggregate_id, payload: second_sink.handle(event_type, aggregate_id, payload),
        claim_seconds=30,
    )
    replay_result = dispatcher_b.dispatch_once()
    assert replay_result == {"delivered": 1, "retried": 0, "selected": 1}
    assert first_sink.snapshot() == [{"event_type": "ORDER_EXECUTED", "aggregate_id": "O-CLAIM-DURABLE", "payload": {"order_id": "O-CLAIM-DURABLE", "volume": 5}}]
    assert second_sink.snapshot() == []
    with session_factory_a() as session:
        event = session.scalar(select(ExecutionOutboxModel).where(ExecutionOutboxModel.event_id == "durable-claim-loss"))
        assert event.status == "PROCESSED"
        assert session.scalar(select(func.count(ConsumedExecutionEventModel.id))) == 1
        assert session.scalar(select(func.count(ExecutionEventProjectionModel.id))) == 1


def test_retry_then_success_produces_one_projection_and_processed_outbox(tmp_path):
    session_factory = _file_session_factory(tmp_path / "retry-durable.db")
    with session_factory() as session:
        ExecutionOutboxRepository(session).enqueue("ORDER_EXECUTED", "O-RETRY-DURABLE", {"order_id": "O-RETRY-DURABLE", "volume": 8}, event_id="durable-retry")
        session.commit()

    sink = DurableExecutionEventSink(session_factory)
    calls = 0

    def flaky_handler(event_type, aggregate_id, payload):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient delivery failure")
        sink.handle(event_type, aggregate_id, payload)

    dispatcher = ExecutionOutboxDispatcher(session_factory, flaky_handler, claim_seconds=30)
    assert dispatcher.dispatch_once() == {"delivered": 0, "retried": 1, "selected": 1}

    with session_factory() as session:
        event = session.scalar(select(ExecutionOutboxModel).where(ExecutionOutboxModel.event_id == "durable-retry"))
        assert event.status == "PENDING"
        assert event.attempts == 1
        assert session.scalar(select(func.count(ConsumedExecutionEventModel.id))) == 0
        assert session.scalar(select(func.count(ExecutionEventProjectionModel.id))) == 0

    assert dispatcher.dispatch_once() == {"delivered": 1, "retried": 0, "selected": 1}
    recreated_sink = DurableExecutionEventSink(session_factory)
    with session_factory() as session:
        event = session.scalar(select(ExecutionOutboxModel).where(ExecutionOutboxModel.event_id == "durable-retry"))
        assert event.status == "PROCESSED"
        assert event.attempts == 1
        assert session.scalar(select(func.count(ConsumedExecutionEventModel.id))) == 1
        assert session.scalar(select(func.count(ExecutionEventProjectionModel.id))) == 1

    assert recreated_sink.durable_snapshot() == [{"event_id": "durable-retry", "event_type": "ORDER_EXECUTED", "aggregate_id": "O-RETRY-DURABLE", "payload": {"order_id": "O-RETRY-DURABLE", "volume": 8}}]


def test_projection_and_consumer_are_atomic_on_projection_failure(tmp_path, monkeypatch):
    session_factory = _file_session_factory(tmp_path / "projection-failure.db")
    sink = DurableExecutionEventSink(session_factory)
    original_save = ExecutionEventProjectionRepository.save

    def fail_save(self, *args, **kwargs):
        original_save(self, *args, **kwargs)
        raise RuntimeError("projection failure")

    monkeypatch.setattr(ExecutionEventProjectionRepository, "save", fail_save)
    try:
        sink.handle("ORDER_EXECUTED", "O-ATOMIC", {"_event_id": "atomic-1", "volume": 1})
    except RuntimeError as exc:
        assert str(exc) == "projection failure"
    else:
        raise AssertionError("projection failure must be raised")

    assert sink.snapshot() == []
    with session_factory() as session:
        assert session.scalar(select(func.count(ConsumedExecutionEventModel.id))) == 0
        assert session.scalar(select(func.count(ExecutionEventProjectionModel.id))) == 0
