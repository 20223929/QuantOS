from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.execution_outbox_dispatcher import ExecutionOutboxDispatcher
from app.storage.models.base import Base


def _new_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_dispatcher_metrics_accumulate_delivery_and_retry_counts():
    session_factory = _new_session_factory()
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-METRIC-FAIL", {"id": 1}, event_id="metric-fail")
        repository.enqueue("ORDER_EXECUTED", "O-METRIC-OK", {"id": 2}, event_id="metric-ok")
        session.commit()

    def handler(_event_type, aggregate_id, _payload):
        if aggregate_id == "O-METRIC-FAIL":
            raise RuntimeError("temporary")

    dispatcher = ExecutionOutboxDispatcher(session_factory, handler)
    assert dispatcher.dispatch_once() == {"delivered": 1, "retried": 1, "selected": 2}
    assert dispatcher.snapshot() == {"delivered": 1, "retried": 1, "selected": 2}


def test_dispatcher_metrics_include_second_attempt():
    session_factory = _new_session_factory()
    with session_factory() as session:
        ExecutionOutboxRepository(session).enqueue(
            "ORDER_EXECUTED", "O-METRIC-RETRY", {"id": 3}, event_id="metric-retry"
        )
        session.commit()

    attempts = []

    def handler(_event_type, aggregate_id, _payload):
        attempts.append(aggregate_id)
        if len(attempts) == 1:
            raise RuntimeError("first attempt")

    dispatcher = ExecutionOutboxDispatcher(session_factory, handler)
    dispatcher.dispatch_once()
    dispatcher.dispatch_once()

    assert dispatcher.snapshot() == {"delivered": 1, "retried": 1, "selected": 2}
