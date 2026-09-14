from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.execution_outbox_dispatcher import ExecutionOutboxDispatcher
from app.storage.models.base import Base
from app.storage.models.outbox import ExecutionOutboxModel
from app.trading.execution_event_sink import ExecutionEventSink


def test_persisted_execution_event_is_delivered_and_marked_processed():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    sink = ExecutionEventSink()

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue(
            event_type="ORDER_EXECUTED",
            aggregate_id="O-INTEGRATION-001",
            event_id="order-executed:O-INTEGRATION-001",
            payload={"status": "FILLED", "volume": 5},
        )
        session.commit()

    dispatcher = ExecutionOutboxDispatcher(session_factory, sink.handle)
    assert dispatcher.dispatch_once() == {"delivered": 1, "retried": 0, "selected": 1}
    assert sink.snapshot()[0]["aggregate_id"] == "O-INTEGRATION-001"

    with session_factory() as session:
        event = session.scalar(select(ExecutionOutboxModel))
        assert event.status == "PROCESSED"


def test_failed_delivery_is_retried_then_delivered():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    sink = ExecutionEventSink()

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue(
            event_type="ORDER_EXECUTED",
            aggregate_id="O-INTEGRATION-002",
            event_id="order-executed:O-INTEGRATION-002",
            payload={"status": "FILLED"},
        )
        session.commit()

    attempts = {"count": 0}

    def flaky_handler(event_type, aggregate_id, payload):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary sink outage")
        sink.handle(event_type, aggregate_id, payload)

    dispatcher = ExecutionOutboxDispatcher(session_factory, flaky_handler)
    assert dispatcher.dispatch_once() == {"delivered": 0, "retried": 1, "selected": 1}
    assert dispatcher.dispatch_once() == {"delivered": 1, "retried": 0, "selected": 1}
    assert len(sink.snapshot()) == 1
