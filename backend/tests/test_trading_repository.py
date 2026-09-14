from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.storage.models.base import Base
from app.storage.trading_repository import TradingRepository


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
        assert updated.status == "SUBMITTED"


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
