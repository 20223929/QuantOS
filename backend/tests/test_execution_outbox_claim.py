from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.models.base import Base


def _new_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_claim_pending_assigns_owner_and_expiry():
    session_factory = _new_session_factory()
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-CLAIM", {"order_id": "O-CLAIM"}, event_id="claim-1")
        session.commit()

        now = datetime(2026, 9, 14, 5, 0, tzinfo=UTC)
        events = repository.claim_pending(10, "worker-a", now=now, claim_seconds=30)
        assert [event.event_id for event in events] == ["claim-1"]
        assert events[0].claim_owner == "worker-a"
        assert events[0].claim_expires_at.replace(tzinfo=UTC) == now + timedelta(seconds=30)
        session.commit()


def test_claim_pending_does_not_take_active_claim_and_recovers_after_expiry():
    session_factory = _new_session_factory()
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-CLAIM", {"order_id": "O-CLAIM"}, event_id="claim-2")
        session.commit()

    start = datetime(2026, 9, 14, 5, 0, tzinfo=UTC)
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        assert repository.claim_pending(10, "worker-a", now=start, claim_seconds=30)
        session.commit()

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        assert repository.claim_pending(10, "worker-b", now=start + timedelta(seconds=10), claim_seconds=30) == []

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        events = repository.claim_pending(10, "worker-b", now=start + timedelta(seconds=31), claim_seconds=30)
        assert [event.event_id for event in events] == ["claim-2"]
        assert events[0].claim_owner == "worker-b"
        session.commit()


def test_only_claim_owner_can_complete_event():
    session_factory = _new_session_factory()
    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-OWNER", {"order_id": "O-OWNER"}, event_id="claim-3")
        session.commit()

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.claim_pending(10, "worker-a")
        session.commit()

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        assert repository.mark_processed("claim-3", owner="worker-b") is None
        event = repository.mark_processed("claim-3", owner="worker-a")
        assert event is not None
        assert event.status == "PROCESSED"
        assert event.claim_owner is None
        assert event.claim_expires_at is None
        session.commit()


def test_renew_claim_extends_expiry_for_current_owner_only():
    session_factory = _new_session_factory()
    start = datetime(2026, 9, 14, 5, 0, tzinfo=UTC)

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-RENEW", {"order_id": "O-RENEW"}, event_id="claim-renew")
        repository.claim_pending(10, "worker-a", now=start, claim_seconds=30)
        renewed = repository.renew_claim("claim-renew", "worker-a", now=start + timedelta(seconds=10), claim_seconds=60)
        assert renewed is not None
        assert renewed.claim_expires_at.replace(tzinfo=UTC) == start + timedelta(seconds=70)
        assert repository.renew_claim("claim-renew", "worker-b", now=start + timedelta(seconds=11), claim_seconds=60) is None
        session.commit()


def test_status_counts_separate_pending_claimed_expired_and_processed():
    session_factory = _new_session_factory()
    start = datetime(2026, 9, 14, 5, 0, tzinfo=UTC)

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        repository.enqueue("ORDER_EXECUTED", "O-PENDING", {}, event_id="status-pending")
        repository.enqueue("ORDER_EXECUTED", "O-CLAIMED", {}, event_id="status-claimed")
        repository.enqueue("ORDER_EXECUTED", "O-EXPIRED", {}, event_id="status-expired")
        repository.enqueue("ORDER_EXECUTED", "O-PROCESSED", {}, event_id="status-processed")
        repository.claim_pending(1, "worker-a", now=start, claim_seconds=30)
        expired = repository.claim_pending(1, "worker-b", now=start, claim_seconds=1)
        assert expired
        expired[0].claim_expires_at = (start - timedelta(seconds=1)).replace(tzinfo=None)
        repository.mark_processed("status-processed")
        session.commit()

    with session_factory() as session:
        repository = ExecutionOutboxRepository(session)
        counts = repository.status_counts(now=start)
        assert counts == {"pending": 1, "claimed": 1, "expired": 1, "processed": 1}
