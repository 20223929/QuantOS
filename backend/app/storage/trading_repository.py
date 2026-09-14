from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.storage.models.trading import MarketDataModel, OrderModel, PositionModel, TradeModel


class TradingRepository:
    """Persistence gateway for orders, trades, positions and market ticks."""

    def __init__(self, session):
        self.session = session

    def save_order(self, order):
        record = OrderModel(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            volume=order.volume,
            price=order.price,
            status=order.status,
            offset=order.offset,
            created_at=datetime.now(UTC),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def update_order_status(self, order_id: str, status: str):
        record = self.session.scalar(select(OrderModel).where(OrderModel.order_id == order_id))
        if record is None:
            return None
        record.status = status
        self.session.flush()
        return record

    def save_trade(self, trade):
        record = TradeModel(
            trade_id=str(trade.get("trade_id") or trade.get("id") or f"trade-{datetime.now(UTC).timestamp()}"),
            order_id=trade.get("order_id"),
            symbol=trade["symbol"],
            side=str(trade["side"]).upper(),
            price=float(trade["price"]),
            volume=float(trade["volume"]),
            created_at=datetime.now(UTC),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def upsert_position(self, symbol: str, volume: float):
        record = self.session.scalar(select(PositionModel).where(PositionModel.symbol == symbol))
        if record is None:
            record = PositionModel(symbol=symbol, volume=volume, updated_at=datetime.now(UTC))
            self.session.add(record)
        else:
            record.volume = volume
            record.updated_at = datetime.now(UTC)
        self.session.flush()
        return record

    def save_market_tick(self, symbol: str, price: float, timestamp=None):
        record = MarketDataModel(
            symbol=symbol,
            price=float(price),
            timestamp=timestamp or datetime.now(UTC),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_orders(self):
        return list(self.session.scalars(select(OrderModel).order_by(OrderModel.id.desc())))

    def list_positions(self):
        return list(self.session.scalars(select(PositionModel).order_by(PositionModel.symbol)))

    def list_market_data(self, symbol: str, limit: int = 200):
        statement = select(MarketDataModel).where(MarketDataModel.symbol == symbol).order_by(MarketDataModel.id.desc()).limit(limit)
        return list(self.session.scalars(statement))
