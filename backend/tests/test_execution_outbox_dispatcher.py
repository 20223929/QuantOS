import threading
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.execution_outbox_dispatcher import ExecutionOutboxDispatcher
from app.storage.models.base import Base
from app.storage.models.outbox import ExecutionOutboxModel


def _new_session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _new_file_session_factory(path):
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_dispatcher_delivers_pending_events_and_marks_processed():
    session_factory = _new_session_factory()
    received = []
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-DISPATCH", {"order_id": "O-DISPATCH", "volume": 2}, event_id="dispatch-1")
        session.commit()

    dispatcher = ExecutionOutboxDispatcher(session_factory, lambda event_type, aggregate_id, payload: received.append((event_type, aggregate_id, payload)))
    result = dispatcher.dispatch_once()
    assert result == {"delivered": 1, "retried": 0, "selected": 1}
    assert received == [("ORDER_EXECUTED", "O-DISPATCH", {"order_id": "O-DISPATCH", "volume": 2, "_event_id": "dispatch-1"})]
    with session_factory() as session:
        assert ExecutionOutboxRepository(session).pending() == []


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
    assert received == [("ORDER_EXECUTED", "O-OK", {"order_id": "O-OK", "_event_id": "dispatch-ok"})]
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
        assert ExecutionOutboxRepository(session).pending() == []


def test_dispatcher_renews_long_running_claim_and_reports_metric():
    session_factory = _new_session_factory()
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-SLOW", {}, event_id="dispatch-slow")
        session.commit()

    dispatcher = ExecutionOutboxDispatcher(session_factory, lambda event_type, aggregate_id, payload: time.sleep(1.2), claim_seconds=1, heartbeat_seconds=0.2)
    result = dispatcher.dispatch_once()
    assert result["delivered"] == 1
    assert dispatcher.snapshot()["claim_renewed"] >= 1
    assert dispatcher.snapshot()["claim_lost"] == 0


def test_dispatcher_commits_claim_before_running_handler(tmp_path):
    db_path = tmp_path / "shared-outbox.db"
    session_factory_a = _new_file_session_factory(db_path)
    session_factory_b = _new_file_session_factory(db_path)
    with session_factory_a() as session:
        ExecutionOutboxRepository(session).enqueue("ORDER_EXECUTED", "O-CONCURRENT", {}, event_id="dispatch-concurrent")
        session.commit()

    handler_started = threading.Event()
    release_handler = threading.Event()
    received = []

    def slow_handler(event_type, aggregate_id, payload):
        handler_started.set()
        release_handler.wait(timeout=5)
        received.append(aggregate_id)

    dispatcher_a = ExecutionOutboxDispatcher(session_factory_a, slow_handler, claim_seconds=5, heartbeat_seconds=1)
    dispatcher_b = ExecutionOutboxDispatcher(session_factory_b, lambda event_type, aggregate_id, payload: received.append(f"duplicate:{aggregate_id}"), claim_seconds=5, heartbeat_seconds=1)

    result_a = {}
    worker = threading.Thread(target=lambda: result_a.update(dispatcher_a.dispatch_once()))
    worker.start()
    assert handler_started.wait(timeout=5)
    result_b = dispatcher_b.dispatch_once()
    assert result_b == {"delivered": 0, "retried": 0, "selected": 0}
    release_handler.set()
    worker.join(timeout=5)
    assert result_a == {"delivered": 1, "retried": 0, "selected": 1}
    assert received == ["O-CONCURRENT"]
    with session_factory_a() as session:
        assert ExecutionOutboxRepository(session).pending() == []


def test_dispatcher_reclaims_expired_claim_from_previous_instance(tmp_path):
    db_path = tmp_path / "recovery-outbox.db"
    session_factory_a = _new_file_session_factory(db_path)
    session_factory_b = _new_file_session_factory(db_path)
    with session_factory_a() as session:
        ExecutionOutboxRepository(session).enqueue("ORDER_EXECUTED", "O-RECOVER", {}, event_id="dispatch-recover")
        session.commit()
    with session_factory_a() as session:
        repository = ExecutionOutboxRepository(session)
        claimed = repository.claim_pending(limit=1, owner="crashed-dispatcher", now=time_now_minus(seconds=60), claim_seconds=30)
        assert len(claimed) == 1
        session.commit()

    received = []
    dispatcher = ExecutionOutboxDispatcher(session_factory_b, lambda event_type, aggregate_id, payload: received.append(aggregate_id))
    result = dispatcher.dispatch_once()
    assert result == {"delivered": 1, "retried": 0, "selected": 1}
    assert received == ["O-RECOVER"]


def test_dispatcher_preserves_distinct_event_ids_for_same_aggregate():
    session_factory = _new_session_factory()
    received = []
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-PARTIAL", {"volume": 2}, event_id="dispatch-partial-1")
        repository.enqueue("ORDER_EXECUTED", "O-PARTIAL", {"volume": 3}, event_id="dispatch-partial-2")
        session.commit()

    dispatcher = ExecutionOutboxDispatcher(session_factory, lambda event_type, aggregate_id, payload: received.append(payload["_event_id"]))
    result = dispatcher.dispatch_once()
    assert result == {"delivered": 2, "retried": 0, "selected": 2}
    assert received == ["dispatch-partial-1", "dispatch-partial-2"]


def test_processed_claim_cannot_be_reused_after_expiry():
    session_factory = _new_session_factory()
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-FENCE", {}, event_id="dispatch-fence")
        claimed = repository.claim_pending(limit=1, owner="worker-a", now=time_now_minus(seconds=60), claim_seconds=1)
        assert len(claimed) == 1
        event_id = claimed[0].id
        session.commit()

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        processed = repository.mark_processed("dispatch-fence", owner="worker-a", now=time_now_minus(seconds=58))
        assert processed is None
        session.rollback()
        event = session.get(ExecutionOutboxModel, event_id)
        assert event.status == "PENDING"
        assert event.claim_owner == "worker-a"


def time_now_minus(*, seconds: int):
    from datetime import UTC, datetime, timedelta
    return datetime.now(UTC) - timedelta(seconds=seconds)
