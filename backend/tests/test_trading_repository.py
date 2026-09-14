from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.storage.models.base import Base
from app.storage.trading_repository import OrderStateTransitionError, TradingRepository


@dataclass
class Order:
    order_id: str = "O001"
    symbol: str = "SHFE.rb"
    side: str = "BUY"
    volume: int = 1
    price: float = 3500.0
    status: str = "FINISHED"
    offset: str = "OPEN"


def _new_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_trading_repository_round_trip():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order())
        repository.upsert_position("SHFE.rb", 1)
        repository.save_market_tick("SHFE.rb", 3501.0, datetime.now(UTC))
        trade = repository.save_trade({
            "trade_id": "T001",
            "order_id": order.order_id,
            "symbol": "SHFE.rb",
            "side": "BUY",
            "price": 3500,
            "volume": 1,
        })
        session.commit()

        assert order.status == "FILLED"
        assert trade.order_id == order.id
        assert len(repository.list_orders()) == 1
        assert len(repository.list_trades()) == 1
        assert len(repository.list_positions()) == 1
        assert len(repository.list_market_data("SHFE.rb")) == 1

        updated = repository.update_order_status("O001", "ALIVE")
        session.commit()
        assert updated.status == "FILLED"


def test_order_write_is_idempotent_and_keeps_single_row():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)

        first = repository.save_order(Order())
        session.commit()
        first_id = first.id
        first_created_at = first.created_at

        second = repository.save_order(Order(volume=2, price=3510.0, status="SUCCESS"))
        session.commit()

        assert second.id == first_id
        assert second.created_at == first_created_at
        assert second.volume == 2
        assert second.price == 3510.0
        assert second.status == "FILLED"
        assert len(repository.list_orders()) == 1


def test_trade_write_is_idempotent_and_links_vendor_order_id():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order())
        session.commit()

        first = repository.save_trade({
            "trade_id": "T-REPLAY",
            "order_id": "O001",
            "symbol": "SHFE.rb",
            "side": "BUY",
            "price": 3500,
            "volume": 1,
        })
        session.commit()
        first_id = first.id

        second = repository.save_trade({
            "trade_id": "T-REPLAY",
            "order_id": "O001",
            "symbol": "SHFE.rb",
            "side": "BUY",
            "price": 3510,
            "volume": 2,
        })
        session.commit()

        assert second.id == first_id
        assert second.order_id == order.id
        assert second.price == 3510
        assert second.volume == 2
        assert len(repository.list_trades()) == 1


def test_partial_fills_advance_lifecycle_and_ignore_duplicate_trade_event():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order(volume=5, status="SUBMITTED"))
        session.commit()

        first = repository.apply_trade({
            "trade_id": "T-PART-1",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "price": order.price,
            "volume": 2,
        })
        session.commit()
        assert first.trade_id == "T-PART-1"
        assert repository.order_filled_volume(order.id) == 2
        assert repository.get_order(order.order_id).status == "PARTIALLY_FILLED"

        duplicate = repository.apply_trade({
            "trade_id": "T-PART-1",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "price": 3501,
            "volume": 2,
        })
        session.commit()
        assert duplicate.id == first.id
        assert repository.order_filled_volume(order.id) == 2
        assert len(repository.list_trades()) == 1

        repository.apply_trade({
            "trade_id": "T-PART-2",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "price": 3502,
            "volume": 3,
        })
        session.commit()
        assert repository.order_filled_volume(order.id) == 5
        assert repository.get_order(order.order_id).status == "FILLED"
        assert len(repository.list_trades()) == 2


def test_cancelled_order_does_not_regress_to_partial_on_late_duplicate_state():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order(volume=5, status="SUBMITTED"))
        session.commit()

        repository.update_order_status(order.order_id, "CANCELLED")
        session.commit()
        repository.apply_trade({
            "trade_id": "T-LATE-FILL",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "price": order.price,
            "volume": 1,
        })
        session.commit()

        assert repository.get_order(order.order_id).status == "CANCELLED"
        assert repository.order_filled_volume(order.id) == 1


def test_order_state_machine_allows_partial_fill_then_cancel_then_late_fill():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order(volume=5, status="SUBMITTED"))
        session.commit()

        repository.update_order_status(order.order_id, "PARTIALLY_FILLED")
        repository.update_order_status(order.order_id, "CANCELLED")
        session.commit()
        assert repository.get_order(order.order_id).status == "CANCELLED"

        repository.apply_trade({
            "trade_id": "T-LATE-2",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "price": order.price,
            "volume": 5,
        })
        session.commit()
        assert repository.get_order(order.order_id).status == "FILLED"
        assert repository.order_filled_volume(order.id) == 5


def test_order_state_machine_rejects_illegal_partial_to_submitted_regression():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order(volume=5, status="SUBMITTED"))
        session.commit()
        repository.update_order_status(order.order_id, "PARTIALLY_FILLED")
        session.commit()

        with pytest.raises(OrderStateTransitionError):
            repository.update_order_status(order.order_id, "SUBMITTED")
        session.rollback()
        assert repository.get_order(order.order_id).status == "PARTIALLY_FILLED"


def test_order_state_machine_ignores_stale_terminal_regressions():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order(volume=5, status="SUBMITTED"))
        session.commit()

        repository.update_order_status(order.order_id, "CANCELLED")
        session.commit()
        repository.update_order_status(order.order_id, "SUBMITTED")
        session.commit()
        assert repository.get_order(order.order_id).status == "CANCELLED"

        repository.update_order_status(order.order_id, "FILLED")
        session.commit()
        assert repository.get_order(order.order_id).status == "FILLED"


def test_order_filled_volume_snapshot_survives_new_repository_instance():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order(volume=5, status="SUBMITTED"))
        repository.apply_trade({
            "trade_id": "T-RESUME-1",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "price": order.price,
            "volume": 2,
        })
        session.commit()

    with Session(engine) as session:
        repository = TradingRepository(session)
        snapshot = repository.order_filled_volumes()
        assert snapshot["O001"] == 2


def test_persisted_state_survives_new_session():
    engine = _new_engine()

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order())
        repository.save_trade({
            "trade_id": "T-SNAPSHOT",
            "order_id": order.order_id,
            "symbol": "SHFE.rb",
            "side": "BUY",
            "price": 3500,
            "volume": 1,
        })
        repository.upsert_position("SHFE.rb", 1)
        session.commit()

    with Session(engine) as session:
        repository = TradingRepository(session)
        persisted_order = repository.get_order("O001")
        persisted_trade = repository.list_trades()[0]
        persisted_position = repository.list_positions()[0]

        assert persisted_order is not None
        assert persisted_order.status == "FILLED"
        assert persisted_trade.trade_id == "T-SNAPSHOT"
        assert persisted_trade.order_id == persisted_order.id
        assert persisted_position.symbol == "SHFE.rb"
        assert persisted_position.volume == 1
