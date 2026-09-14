from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select

from app.storage.models.trading import MarketDataModel, OrderModel, PositionModel, TradeModel


_STATUS_ALIASES = {
    "FINISHED": "FILLED",
    "SUCCESS": "FILLED",
    "ALIVE": "SUBMITTED",
    "PENDING": "SUBMITTED",
}


def _canonical_status(status: str) -> str:
    normalized = str(status or "").upper()
    return _STATUS_ALIASES.get(normalized, normalized)


class TradingRepository:
    """Persistence gateway for trading state with idempotent event writes."""

    def __init__(self, session):
        self.session = session

    def save_order(self, order):
        order_id = getattr(order, "order_id", None)
        record = None
        if order_id:
            record = self.session.scalar(select(OrderModel).where(OrderModel.order_id == str(order_id)))

        status = _canonical_status(getattr(order, "status", "PENDING"))
        if record is None:
            record = OrderModel(
                order_id=str(order_id) if order_id else None,
                symbol=order.symbol,
                side=str(order.side).upper(),
                volume=float(order.volume),
                price=order.price,
                status=status,
                offset=str(getattr(order, "offset", "OPEN")).upper(),
                created_at=getattr(order, "created_at", None) or datetime.now(UTC),
            )
            self.session.add(record)
        else:
            record.symbol = order.symbol
            record.side = str(order.side).upper()
            record.volume = float(order.volume)
            record.price = order.price
            record.status = status
            record.offset = str(getattr(order, "offset", "OPEN")).upper()
        self.session.flush()
        return record

    def update_order_status(self, order_id: str, status: str):
        record = self.session.scalar(select(OrderModel).where(OrderModel.order_id == str(order_id)))
        if record is None:
            return None
        record.status = _canonical_status(status)
        self.session.flush()
        return record

    def get_order(self, order_id: str):
        return self.session.scalar(select(OrderModel).where(OrderModel.order_id == str(order_id)))

    def save_trade(self, trade):
        trade_id = str(trade.get("trade_id") or trade.get("id") or uuid4())
        with self.session.no_autoflush:
            record = self.session.scalar(select(TradeModel).where(TradeModel.trade_id == trade_id))
            raw_order_id = trade.get("order_id")
            internal_order_id = None
            if isinstance(raw_order_id, int):
                internal_order_id = raw_order_id
            elif raw_order_id is not None:
                raw_order_id_str = str(raw_order_id)
                linked_order = self.session.scalar(
                    select(OrderModel).where(OrderModel.order_id == raw_order_id_str)
                )
                internal_order_id = linked_order.id if linked_order is not None else (
                    int(raw_order_id_str) if raw_order_id_str.isdigit() else None
                )

            if record is None:
                record = TradeModel(trade_id=trade_id, created_at=datetime.now(UTC))
                self.session.add(record)

            record.order_id = internal_order_id
            record.symbol = str(trade["symbol"])
            record.side = str(trade["side"]).upper()
            record.price = float(trade["price"])
            record.volume = float(trade["volume"])
        self.session.flush()
        return record

    def apply_trade(self, trade):
        """Persist a trade event once and derive the linked order lifecycle state."""
        trade_id = str(trade.get("trade_id") or trade.get("id") or "")
        existing = self.session.scalar(select(TradeModel).where(TradeModel.trade_id == trade_id))
        if existing is not None:
            return existing

        record = self.save_trade(trade)

        if record.order_id is not None:
            order = self.session.get(OrderModel, record.order_id)
            if order is not None:
                filled_volume = self.session.scalar(
                    select(func.coalesce(func.sum(TradeModel.volume), 0.0)).where(
                        TradeModel.order_id == order.id
                    )
                )
                requested = float(order.volume)
                if filled_volume >= requested:
                    order.status = "FILLED"
                elif filled_volume > 0:
                    order.status = "PARTIALLY_FILLED"
                self.session.flush()
        return record

    def upsert_position(self, symbol: str, volume: float):
        record = self.session.scalar(select(PositionModel).where(PositionModel.symbol == symbol))
        if record is None:
            record = PositionModel(symbol=symbol, volume=float(volume), updated_at=datetime.now(UTC))
            self.session.add(record)
        else:
            record.volume = float(volume)
            record.updated_at = datetime.now(UTC)
        self.session.flush()
        return record

    def recover_positions_from_trades(self):
        """Rebuild positions from committed trades, including clearing stale symbols."""
        trades = self.list_trades()
        net: dict[str, float] = {}
        for trade in trades:
            multiplier = 1.0 if trade.side.upper() in {"BUY", "LONG"} else -1.0
            net[trade.symbol] = net.get(trade.symbol, 0.0) + multiplier * float(trade.volume)

        existing_positions = self.list_positions()
        known_symbols = set(net)
        for position in existing_positions:
            if position.symbol not in known_symbols:
                net[position.symbol] = 0.0

        for symbol, volume in net.items():
            self.upsert_position(symbol, volume)
        return net

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

    def list_trades(self):
        return list(self.session.scalars(select(TradeModel).order_by(TradeModel.id.desc())))

    def list_positions(self):
        return list(self.session.scalars(select(PositionModel).order_by(PositionModel.symbol)))

    def list_market_data(self, symbol: str, limit: int = 200):
        statement = (
            select(MarketDataModel)
            .where(MarketDataModel.symbol == symbol)
            .order_by(MarketDataModel.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
