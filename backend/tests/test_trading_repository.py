from datetime import UTC, datetime

from sqlalchemy import create_engine

from app.storage.models.base import Base
from app.storage.models.trading import MarketDataModel, OrderModel, PositionModel, TradeModel
from app.storage.trading_repository import TradingRepository


class Order:
    order_id = "O001"
    symbol = "SHFE.rb"
    side = "BUY"
    volume = 1
    price = 3500.0
    status = "FILLED"
    offset = "OPEN"


def test_trading_repository_round_trip():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        repository = TradingRepository(session)
        order = repository.save_order(Order())
        assert order.order_id == "O001"

        repository.upsert_position("SHFE.rb", 1)
        repository.save_market_tick("SHFE.rb", 3501.0, datetime.now(UTC))
        repository.save_trade({
            "trade_id": "T001",
            "order_id": order.id,
            "symbol": "SHFE.rb",
            "side": "BUY",
            "price": 3500,
            "volume": 1,
        })
        session.commit()

        assert len(repository.list_orders()) == 1
        assert len(repository.list_positions()) == 1
        assert len(repository.list_market_data("SHFE.rb")) == 1

        updated = repository.update_order_status("O001", "FINISHED")
        session.commit()
        assert updated.status == "FINISHED"
