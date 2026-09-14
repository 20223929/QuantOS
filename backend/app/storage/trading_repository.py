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
    "PARTIAL_FILLED": "PARTIALLY_FILLED",
    "PARTIALLYFILLED": "PARTIALLY_FILLED",
}

_ORDER_TRANSITIONS = {
    "SUBMITTED": {"SUBMITTED", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED"},
    "PARTIALLY_FILLED": {"PARTIALLY_FILLED", "FILLED", "CANCELLED"},
    "FILLED": {"FILLED"},
    "CANCELLED": {"CANCELLED", "FILLED"},
    "REJECTED": {"REJECTED"},
}
_TERMINAL_STATUSES = {"FILLED", "CANCELLED", "REJECTED"}


class OrderStateTransitionError(ValueError):
    """Raised when an order lifecycle update would move to an invalid state."""

    def __init__(self, current: str, requested: str):
        self.current = current
        self.requested = requested
        super().__init__(f"invalid order state transition: {current} -> {requested}")


def _canonical_status(status: str) -> str:
    normalized = str(status or "").upper()
    return _STATUS_ALIASES.get(normalized, normalized)


def _merge_order_status(current: str, requested: str) -> str:
    current = _canonical_status(current)
    requested = _canonical_status(requested)
    if current == requested:
        return current
    if current in _TERMINAL_STATUSES:
        if current == "CANCELLED" and requested == "FILLED":
            return requested
        return current
    if requested == "PENDING":
        return current
    allowed = _ORDER_TRANSITIONS.get(current)
    if allowed is not None and requested in allowed:
        return requested
    if current == "" and requested:
        return requested
    raise OrderStateTransitionError(current, requested)


class TradingRepository:
    """Persistence gateway for trading state with idempotent event writes."""

    def __init__(self, session):
        self.session = session

    def save_order(self, order):
        order_id = getattr(order, "order_id", None)
        record = None
        if order_id:
            record = self.session.scalar(select(OrderModel).where(OrderModel.order_id == str(order_id)))

        requested_status = _canonical_status(getattr(order, "status", "PENDING"))
        reason = str(getattr(order, "reason", "") or "")
        if record is None:
            record = OrderModel(
                order_id=str(order_id) if order_id else None,
                symbol=order.symbol,
                side=str(order.side).upper(),
                volume=float(order.volume),
                price=order.price,
                status=requested_status,
                reason=reason,
                offset=str(getattr(order, "offset", "OPEN")).upper(),
                created_at=getattr(order, "created_at", None) or datetime.now(UTC),
            )
            self.session.add(record)
        else:
            record.symbol = order.symbol
            record.side = str(order.side).upper()
            record.volume = float(order.volume)
            record.price = order.price
            record.status = _merge_order_status(record.status, requested_status)
            record.reason = reason
            record.offset = str(getattr(order, "offset", "OPEN")).upper()
        self.session.flush()
        return record

    def update_order_status(self, order_id: str, status: str):
        record = self.session.scalar(select(OrderModel).where(OrderModel.order_id == str(order_id)))
        if record is None:
            return None
        record.status = _merge_order_status(record.status, status)
        self.session.flush()
        return record

    def get_order(self, order_id: str):
        return self.session.scalar(select(OrderModel).where(OrderModel.order_id == str(order_id)))

    def order_filled_volume(self, order_id: int | str) -> float:
        internal_order_id = order_id
        if not isinstance(order_id, int):
            record = self.session.scalar(select(OrderModel).where(OrderModel.order_id == str(order_id)))
            if record is None:
                return 0.0
            internal_order_id = record.id
        value = self.session.scalar(
            select(func.coalesce(func.sum(TradeModel.volume), 0.0)).where(
                TradeModel.order_id == internal_order_id
            )
        )
        return float(value or 0.0)

    def order_filled_volumes(self) -> dict[str, float]:
        rows = self.session.execute(
            select(
                OrderModel.order_id,
                func.coalesce(func.sum(TradeModel.volume), 0.0),
            )
            .outerjoin(TradeModel, TradeModel.order_id == OrderModel.id)
            .group_by(OrderModel.id, OrderModel.order_id)
        )
        return {str(order_id): float(volume or 0.0) for order_id, volume in rows if order_id is not None}

    def reconcile_order_states_from_trades(self) -> int:
        """Reconcile durable order lifecycle state from the authoritative trade ledger."""
        changed = 0
        for record in self.list_orders():
            filled_volume = self.order_filled_volume(record.id)
            if filled_volume <= 0:
                continue

            if filled_volume >= float(record.volume):
                target_status = "FILLED"
            elif record.status not in {"CANCELLED", "REJECTED"}:
                target_status = "PARTIALLY_FILLED"
            else:
                continue

            merged_status = _merge_order_status(record.status, target_status)
            if merged_status != record.status:
                record.status = merged_status
                changed += 1

        self.session.flush()
        return changed

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
                filled_volume = self.order_filled_volume(order.id)
                requested = float(order.volume)
                if filled_volume >= requested:
                    order.status = "FILLED"
                elif filled_volume > 0 and order.status not in {"CANCELLED", "REJECTED"}:
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
