import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.execution_outbox_dispatcher import ExecutionOutboxDispatcher
from app.storage.models.base import Base


def _new_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_dispatcher_delivers_pending_events_and_marks_processed():
    session_factory = _new_session_factory()
    received = []

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue(
            "ORDER_EXECUTED",
            "O-DISPATCH",
            {"order_id": "O-DISPATCH", "volume": 2},
            event_id="dispatch-1",
        )
        session.commit()

    def handler(event_type, aggregate_id, payload):
        received.append((event_type, aggregate_id, payload))

    dispatcher = ExecutionOutboxDispatcher(session_factory, handler)
    result = dispatcher.dispatch_once()

    assert result == {"delivered": 1, "retried": 0, "selected": 1}
    assert received == [("ORDER_EXECUTED", "O-DISPATCH", {"order_id": "O-DISPATCH", "volume": 2})]

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        assert repository.pending() == []


def test_dispatcher_retries_failed_event_and_continues_other_events():
    session_factory = _new_session_factory()

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-FAIL", {"order_id": "O-FAIL"}, event_id="dispatch-fail")
        repository.enqueue("ORDER_EXECUTED", "O-OK", {"order_id": "O-OK"}, event_id="dispatch-ok")
        session.commit()

    received = []

    def handler(event_type, aggregate_id, payload):
        if aggregate_id == "O-FAIL":
            raise RuntimeError("temporary downstream failure")
        received.append((event_type, aggregate_id, payload))

    dispatcher = ExecutionOutboxDispatcher(session_factory, handler)
    result = dispatcher.dispatch_once()

    assert result == {"delivered": 1, "retried": 1, "selected": 2}
    assert received == [("ORDER_EXECUTED", "O-OK", {"order_id": "O-OK"})]

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        pending = repository.pending()
        assert [event.event_id for event in pending] == ["dispatch-fail"]
        assert pending[0].attempts == 1


def test_dispatcher_recovers_pending_event_on_next_run():
    session_factory = _new_session_factory()
    attempts = []

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-RETRY", {"order_id": "O-RETRY"}, event_id="dispatch-retry")
        session.commit()

    def flaky_handler(event_type, aggregate_id, payload):
        attempts.append(aggregate_id)
        if len(attempts) == 1:
            raise RuntimeError("first attempt fails")

    dispatcher = ExecutionOutboxDispatcher(session_factory, flaky_handler)
    first = dispatcher.dispatch_once()
    second = dispatcher.dispatch_once()

    assert first["retried"] == 1
    assert second["delivered"] == 1
    assert attempts == ["O-RETRY", "O-RETRY"]

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        assert repository.pending() == []


def test_dispatcher_renews_long_running_claim_and_reports_metric():
    session_factory = _new_session_factory()
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-SLOW", {}, event_id="dispatch-slow")
        session.commit()

    def slow_handler(event_type, aggregate_id, payload):
        time.sleep(1.2)

    dispatcher = ExecutionOutboxDispatcher(
        session_factory,
        slow_handler,
        claim_seconds=1,
        heartbeat_seconds=0.2,
    )
    result = dispatcher.dispatch_once()

    assert result["delivered"] == 1
    assert dispatcher.snapshot()["claim_renewed"] >= 1
    assert dispatcher.snapshot()["claim_lost"] == 0
