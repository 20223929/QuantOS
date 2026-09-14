from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.storage.models.base import Base
from app.storage.models.trading import OrderModel, TradeModel
from app.storage.trading_repository import TradingRepository


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
