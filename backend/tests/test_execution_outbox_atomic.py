from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.storage.execution_outbox import ExecutionOutboxRepository
from app.storage.models.base import Base
from app.storage.models.outbox import ExecutionOutboxModel
from app.storage.models.trading import OrderModel, PositionModel, TradeModel
from app.storage.trading_repository import TradingRepository


@dataclass
class Order:
    order_id: str = "O-OUTBOX-001"
    symbol: str = "SHFE.rb"
    side: str = "BUY"
    volume: int = 5
    price: float = 3500.0
    status: str = "FILLED"
    offset: str = "OPEN"


def _new_engine():
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _trade(order: Order, *, trade_id: str | None = None, volume: float | None = None):
    return {
        "trade_id": trade_id or f"trade-{order.order_id}",
        "order_id": order.order_id,
        "symbol": order.symbol,
        "side": order.side,
        "price": order.price,
        "volume": volume if volume is not None else order.volume,
    }


def _enqueue_execution(session, order: Order, position_volume: int):
    repository = TradingRepository(session)
    outbox = ExecutionOutboxRepository(session)
    record = repository.save_order(order)
    trade = _trade(order)
    trade["order_id"] = record.id
    repository.apply_trade(trade)
    repository.upsert_position(order.symbol, position_volume)
    outbox.enqueue(
        event_type="ORDER_EXECUTED",
        aggregate_id=order.order_id,
        event_id=f"order-executed:{order.order_id}",
        payload={
            "order": {
                "id": order.order_id,
                "symbol": order.symbol,
                "side": order.side,
                "volume": order.volume,
                "price": order.price,
                "offset": order.offset,
                "status": order.status,
            },
            "trade": trade,
            "position": {"symbol": order.symbol, "volume": position_volume},
        },
    )


def test_order_trade_position_and_outbox_commit_together():
    engine = _new_engine()

    with Session(engine) as session:
        _enqueue_execution(session, Order(), 5)
        session.commit()

        assert session.scalar(select(func.count(OrderModel.id))) == 1
        assert session.scalar(select(func.count(TradeModel.id))) == 1
        assert session.scalar(select(func.count(PositionModel.id))) == 1
        event = session.scalar(select(ExecutionOutboxModel))
        assert event.event_type == "ORDER_EXECUTED"
        assert event.aggregate_id == "O-OUTBOX-001"
        assert event.status == "PENDING"


def test_outbox_rolls_back_with_order_trade_and_position():
    engine = _new_engine()

    with Session(engine) as session:
        _enqueue_execution(session, Order(order_id="O-OUTBOX-ROLLBACK"), 5)
        session.rollback()

        assert session.scalar(select(func.count(OrderModel.id))) == 0
        assert session.scalar(select(func.count(TradeModel.id))) == 0
        assert session.scalar(select(func.count(PositionModel.id))) == 0
        assert session.scalar(select(func.count(ExecutionOutboxModel.id))) == 0


def test_execution_outbox_event_is_idempotent_by_event_id():
    engine = _new_engine()

    with Session(engine) as session:
        repository = ExecutionOutboxRepository(session)
        first = repository.enqueue(
            event_type="ORDER_EXECUTED",
            aggregate_id="O-OUTBOX-DUP",
            event_id="order-executed:O-OUTBOX-DUP",
            payload={"status": "FILLED"},
        )
        session.commit()

        second = repository.enqueue(
            event_type="ORDER_EXECUTED",
            aggregate_id="O-OUTBOX-DUP",
            event_id="order-executed:O-OUTBOX-DUP",
            payload={"status": "FILLED"},
        )
        session.commit()

        assert second.id == first.id
        assert session.scalar(select(func.count(ExecutionOutboxModel.id))) == 1


def test_apply_trade_is_idempotent_and_preserves_filled_order_state():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = Order(order_id="O-TRADE-DUP", volume=5)
        repository.save_order(order)

        first = repository.apply_trade(_trade(order, trade_id="T-DUP"))
        second = repository.apply_trade(_trade(order, trade_id="T-DUP"))
        session.commit()

        assert first.id == second.id
        assert session.scalar(select(func.count(TradeModel.id))) == 1
        persisted_order = repository.get_order(order.order_id)
        assert persisted_order.status == "FILLED"


def test_apply_trade_transitions_partial_fill_to_filled():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = Order(order_id="O-PARTIAL", volume=5)
        record = repository.save_order(order)

        partial = _trade(order, trade_id="T-PARTIAL", volume=2)
        partial["order_id"] = record.id
        repository.apply_trade(partial)
        assert repository.get_order(order.order_id).status == "PARTIALLY_FILLED"

        final = _trade(order, trade_id="T-FINAL", volume=3)
        final["order_id"] = record.id
        repository.apply_trade(final)
        session.commit()

        assert session.scalar(select(func.count(TradeModel.id))) == 2
        assert repository.get_order(order.order_id).status == "FILLED"


def test_position_recovery_clears_stale_symbols():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        repository.upsert_position("SHFE.rb", 5)
        repository.upsert_position("DCE.i", 7)
        repository.apply_trade(
            {
                "trade_id": "T-RB-1",
                "order_id": None,
                "symbol": "SHFE.rb",
                "side": "SELL",
                "price": 3500,
                "volume": 2,
            }
        )
        session.commit()

        net = repository.recover_positions_from_trades()
        session.commit()

        assert net == {"SHFE.rb": -2.0, "DCE.i": 0.0}
        assert session.scalar(select(PositionModel.volume).where(PositionModel.symbol == "SHFE.rb")) == -2.0
        assert session.scalar(select(PositionModel.volume).where(PositionModel.symbol == "DCE.i")) == 0.0
