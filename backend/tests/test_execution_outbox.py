from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.models.base import Base
from app.storage.models.outbox import ExecutionOutboxModel


def _new_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_execution_event_is_durable_and_idempotent():
    engine = _new_engine()

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        first = repository.enqueue(
            "ORDER_EXECUTED",
            "O-OUTBOX",
            {"order_id": "O-OUTBOX", "volume": 3},
            event_id="execution-O-OUTBOX",
        )
        session.commit()
        first_id = first.id

        second = repository.enqueue(
            "ORDER_EXECUTED",
            "O-OUTBOX",
            {"order_id": "O-OUTBOX", "volume": 999},
            event_id="execution-O-OUTBOX",
        )
        session.commit()

        assert second.id == first_id
        assert second.payload == '{"order_id":"O-OUTBOX","volume":3}'
        assert len(repository.pending()) == 1


def test_execution_event_retry_increments_attempts_then_can_be_processed():
    engine = _new_engine()

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        event = repository.enqueue(
            "ORDER_EXECUTED",
            "O-RETRY",
            {"order_id": "O-RETRY"},
            event_id="execution-O-RETRY",
        )
        event_id = event.event_id
        session.commit()

        retried = repository.mark_retry(event_id)
        session.commit()
        assert retried.status == "PENDING"
        assert retried.attempts == 1
        assert repository.pending()[0].event_id == "execution-O-RETRY"

        processed = repository.mark_processed(event_id)
        session.commit()
        assert processed.status == "PROCESSED"
        assert processed.processed_at is not None
        assert repository.pending() == []


def test_execution_event_survives_new_session():
    engine = _new_engine()

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue(
            "ORDER_EXECUTED",
            "O-RESTART",
            {"symbol": "SHFE.rb", "volume": 2},
            event_id="execution-O-RESTART",
        )
        session.commit()

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        pending = repository.pending()
        assert len(pending) == 1
        assert pending[0].aggregate_id == "O-RESTART"
        assert pending[0].status == "PENDING"
        assert isinstance(pending[0], ExecutionOutboxModel)


def test_processed_event_is_not_redelivered_after_restart():
    engine = _new_engine()

    event_id = "execution-O-PROCESSED"
    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue(
            "ORDER_EXECUTED",
            "O-PROCESSED",
            {"order_id": "O-PROCESSED"},
            event_id=event_id,
        )
        session.commit()

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        processed = repository.mark_processed(event_id)
        session.commit()
        assert processed.status == "PROCESSED"

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        assert repository.pending() == []
        counts = repository.status_counts()
        assert counts["processed"] == 1
        assert counts["pending"] == 0
        assert counts["claimed"] == 0
        assert counts["expired"] == 0


def test_retry_event_is_replayable_after_restart_without_resetting_attempt_count():
    engine = _new_engine()

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        event = repository.enqueue(
            "ORDER_EXECUTED",
            "O-REPLAY",
            {"order_id": "O-REPLAY", "volume": 1},
            event_id="execution-O-REPLAY",
        )
        event_id = event.event_id
        session.commit()

        repository.mark_retry(event_id)
        session.commit()
        assert event.attempts == 1

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        pending = repository.pending()
        assert len(pending) == 1
        assert pending[0].attempts == 1

        repository.mark_processed(pending[0].event_id)
        session.commit()

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        assert repository.pending() == []
        assert repository.status_counts()["processed"] == 1
