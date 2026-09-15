from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.storage.consumed_events import ConsumedExecutionEventRepository
from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.execution_projection import ExecutionEventProjectionRepository
from app.storage.models.base import Base
from app.storage.models.consumption import ConsumedExecutionEventModel
from app.storage.models.execution_projection import ExecutionEventProjectionModel
from app.storage.models.outbox import ExecutionOutboxModel
from app.storage.models.trading import OrderModel, PositionModel, TradeModel
from app.storage.trading_repository import TradingRepository
from app.trading.durable_execution_event_sink import DurableExecutionEventSink


@dataclass
class Order:
    order_id: str = "O-TX-001"
    symbol: str = "SHFE.rb"
    side: str = "BUY"
    volume: int = 10
    price: float = 3500.0
    status: str = "SUBMITTED"
    offset: str = "OPEN"


def _new_engine():
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _trade(trade_id: str, order_id: str, volume: int, side: str = "BUY"):
    return {
        "trade_id": trade_id,
        "order_id": order_id,
        "symbol": "SHFE.rb",
        "side": side,
        "price": 3500,
        "volume": volume,
    }


def _projection_payloads(session, event_id: str):
    rows = list(
        session.scalars(
            select(ExecutionEventProjectionModel).where(
                ExecutionEventProjectionModel.event_id == event_id
            )
        )
    )
    return rows


def test_failed_trade_write_rolls_back_order_trade_and_position():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.save_order(Order(order_id="O-ROLLBACK"))
        repository.upsert_position("SHFE.rb", 10)

        with pytest.raises((KeyError, ValueError, TypeError)):
            repository.save_trade(
                {
                    "trade_id": "T-ROLLBACK",
                    "order_id": "O-ROLLBACK",
                    "symbol": "SHFE.rb",
                    "side": "BUY",
                    "price": "not-a-price",
                    "volume": 1,
                }
            )
        session.rollback()

        assert session.scalar(select(func.count(OrderModel.id))) == 0
        assert session.scalar(select(func.count(TradeModel.id))) == 0
        assert repository.list_positions() == []


def test_partial_fills_transition_submitted_to_partial_then_filled():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.save_order(Order(order_id="O-PARTIAL", volume=10))
        session.commit()

        repository.apply_trade(_trade("T-P1", "O-PARTIAL", 4))
        session.commit()
        order = repository.get_order("O-PARTIAL")
        assert order.status == "PARTIALLY_FILLED"

        repository.apply_trade(_trade("T-P2", "O-PARTIAL", 6))
        session.commit()
        order = repository.get_order("O-PARTIAL")
        assert order.status == "FILLED"
        assert session.scalar(select(func.sum(TradeModel.volume))) == 10


def test_duplicate_trade_callback_does_not_change_filled_volume_or_status():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.save_order(Order(order_id="O-DUP", volume=5))
        session.commit()

        event = _trade("T-DUP", "O-DUP", 5)
        first = repository.apply_trade(event)
        session.commit()
        first_id = first.id

        second = repository.apply_trade(event)
        session.commit()

        assert second.id == first_id
        assert repository.get_order("O-DUP").status == "FILLED"
        assert session.scalar(select(func.count(TradeModel.id))) == 1
        assert session.scalar(select(func.sum(TradeModel.volume))) == 5


def test_duplicate_trade_callback_keeps_original_payload():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.save_order(Order(order_id="O-DUP-PAYLOAD", volume=5))
        session.commit()

        first = repository.apply_trade(_trade("T-DUP-PAYLOAD", "O-DUP-PAYLOAD", 5))
        session.commit()

        conflicting = _trade("T-DUP-PAYLOAD", "O-DUP-PAYLOAD", 1)
        second = repository.apply_trade(conflicting)
        session.commit()

        assert second.id == first.id
        assert second.volume == 5
        assert repository.get_order("O-DUP-PAYLOAD").status == "FILLED"
        assert session.scalar(select(func.count(TradeModel.id))) == 1
        assert session.scalar(select(func.sum(TradeModel.volume))) == 5


def test_restart_recovery_rebuilds_position_from_committed_trades():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.save_order(Order(order_id="O-RECOVER-BUY", volume=4))
        repository.save_order(Order(order_id="O-RECOVER-SELL", side="SELL", volume=2))
        repository.save_trade(_trade("T-R1", "O-RECOVER-BUY", 4, "BUY"))
        repository.save_trade(_trade("T-R2", "O-RECOVER-SELL", 2, "SELL"))
        repository.upsert_position("SHFE.rb", 999)
        session.commit()

    with Session(engine) as session:
        repository = TradingRepository(session)
        recovered = repository.recover_positions_from_trades()
        session.commit()

        assert recovered["SHFE.rb"] == 2
        assert repository.list_positions()[0].volume == 2


def test_restart_recovery_reconciles_order_state_and_fill_cache_from_trade_ledger():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.save_order(Order(order_id="O-REPLAY", volume=10, status="SUBMITTED"))
        repository.save_trade(_trade("T-REPLAY-1", "O-REPLAY", 4))
        session.commit()

    with Session(engine) as session:
        repository = TradingRepository(session)
        changed = repository.reconcile_order_states_from_trades()
        session.commit()

        assert changed == 1
        assert repository.get_order("O-REPLAY").status == "PARTIALLY_FILLED"
        assert repository.order_filled_volumes() == {"O-REPLAY": 4.0}

        replay = repository.apply_trade(_trade("T-REPLAY-1", "O-REPLAY", 4))
        session.commit()
        assert replay.volume == 4
        assert repository.order_filled_volume("O-REPLAY") == 4
        assert repository.get_order("O-REPLAY").status == "PARTIALLY_FILLED"


def test_cancel_then_late_fill_converges_to_filled_from_authoritative_trade_ledger():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.save_order(Order(order_id="O-RACE", volume=10, status="SUBMITTED"))
        session.commit()

        repository.update_order_status("O-RACE", "CANCELLED")
        session.commit()
        assert repository.get_order("O-RACE").status == "CANCELLED"

        repository.apply_trade(_trade("T-RACE-LATE", "O-RACE", 10))
        session.commit()
        assert repository.get_order("O-RACE").status == "FILLED"
        assert repository.order_filled_volume("O-RACE") == 10

        recovered = repository.recover_positions_from_trades()
        session.commit()
        assert recovered["SHFE.rb"] == 10
        assert repository.list_positions()[0].volume == 10


def test_outbox_replay_survives_new_session_and_event_id_deduplication():
    engine = _new_engine()

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        first = repository.enqueue(
            "ORDER_EXECUTED",
            "O-OUTBOX-REPLAY",
            {"order_id": "O-OUTBOX-REPLAY", "volume": 4},
            event_id="evt-outbox-replay",
        )
        session.commit()
        first_id = first.id

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        pending = repository.pending()
        assert len(pending) == 1
        assert pending[0].id == first_id

        duplicate = repository.enqueue(
            "ORDER_EXECUTED",
            "O-OUTBOX-REPLAY",
            {"order_id": "O-OUTBOX-REPLAY", "volume": 999},
            event_id="evt-outbox-replay",
        )
        session.commit()

        assert duplicate.id == first_id
        assert duplicate.payload == '{"order_id":"O-OUTBOX-REPLAY","volume":4}'
        assert session.scalar(select(func.count(ExecutionOutboxModel.id))) == 1


def test_restart_recovery_is_idempotent_when_run_multiple_times():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.save_order(Order(order_id="O-IDEMPOTENT", volume=3))
        repository.apply_trade(_trade("T-IDEMPOTENT", "O-IDEMPOTENT", 3))
        repository.upsert_position("SHFE.rb", -100)
        session.commit()

    with Session(engine) as session:
        repository = TradingRepository(session)
        first = repository.recover_positions_from_trades()
        session.commit()
        second = repository.recover_positions_from_trades()
        repository.reconcile_order_states_from_trades()
        session.commit()

        assert first == second == {"SHFE.rb": 3.0}
        assert repository.list_positions()[0].volume == 3
        assert repository.get_order("O-IDEMPOTENT").status == "FILLED"
        assert session.scalar(select(func.count(TradeModel.id))) == 1


def test_partial_fill_projection_matches_each_business_fill():
    engine = _new_engine()
    sink = DurableExecutionEventSink(lambda: Session(engine))

    events = [
        ("evt-partial-2", {"order_id": "O-PROJ-PARTIAL", "status": "PARTIALLY_FILLED", "filled_volume": 2}),
        ("evt-partial-5", {"order_id": "O-PROJ-PARTIAL", "status": "FILLED", "filled_volume": 5}),
    ]
    for event_id, payload in events:
        sink.handle("ORDER_EXECUTED", "O-PROJ-PARTIAL", {"_event_id": event_id, **payload})

    with Session(engine) as session:
        projections = list(
            session.scalars(
                select(ExecutionEventProjectionModel).order_by(ExecutionEventProjectionModel.id)
            )
        )
        consumed = list(
            session.scalars(
                select(ConsumedExecutionEventModel).order_by(ConsumedExecutionEventModel.id)
            )
        )
        assert [row.event_id for row in consumed] == ["evt-partial-2", "evt-partial-5"]
        assert [row.event_id for row in projections] == ["evt-partial-2", "evt-partial-5"]
        assert [row.aggregate_id for row in projections] == ["O-PROJ-PARTIAL", "O-PROJ-PARTIAL"]

        import json

        payloads = [json.loads(row.payload) for row in projections]
        assert [payload["filled_volume"] for payload in payloads] == [2, 5]
        assert [payload["status"] for payload in payloads] == ["PARTIALLY_FILLED", "FILLED"]


def test_cancel_then_late_fill_projection_preserves_authoritative_fill_event():
    engine = _new_engine()
    sink = DurableExecutionEventSink(lambda: Session(engine))

    sink.handle(
        "ORDER_EXECUTED",
        "O-PROJ-RACE",
        {
            "_event_id": "evt-late-fill",
            "order_id": "O-PROJ-RACE",
            "status": "FILLED",
            "filled_volume": 10,
            "cancel_requested": True,
        },
    )

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.save_order(Order(order_id="O-PROJ-RACE", volume=10, status="CANCELLED"))
        repository.apply_trade(_trade("T-PROJ-RACE", "O-PROJ-RACE", 10))
        session.commit()

        row = session.scalar(
            select(ExecutionEventProjectionModel).where(
                ExecutionEventProjectionModel.event_id == "evt-late-fill"
            )
        )
        assert row.aggregate_id == "O-PROJ-RACE"
        import json

        payload = json.loads(row.payload)
        assert payload["status"] == "FILLED"
        assert payload["filled_volume"] == 10
        assert repository.get_order("O-PROJ-RACE").status == "FILLED"


def test_projection_query_is_idempotent_across_restart_for_business_events():
    engine = _new_engine()
    session_factory = lambda: Session(engine)
    first = DurableExecutionEventSink(session_factory)
    first.handle("ORDER_EXECUTED", "O-PROJ-RESTART", {"_event_id": "evt-restart-1", "status": "PARTIALLY_FILLED", "filled_volume": 3})
    first.handle("ORDER_EXECUTED", "O-PROJ-RESTART", {"_event_id": "evt-restart-2", "status": "FILLED", "filled_volume": 6})

    recreated = DurableExecutionEventSink(session_factory)
    assert recreated.snapshot() == []
    assert recreated.durable_snapshot(aggregate_id="O-PROJ-RESTART") == [
        {"event_id": "evt-restart-1", "event_type": "ORDER_EXECUTED", "aggregate_id": "O-PROJ-RESTART", "payload": {"filled_volume": 3, "status": "PARTIALLY_FILLED"}},
        {"event_id": "evt-restart-2", "event_type": "ORDER_EXECUTED", "aggregate_id": "O-PROJ-RESTART", "payload": {"filled_volume": 6, "status": "FILLED"}},
    ]

    with Session(engine) as session:
        assert session.scalar(select(func.count(ConsumedExecutionEventModel.id))) == 2
        assert session.scalar(select(func.count(ExecutionEventProjectionModel.id))) == 2
