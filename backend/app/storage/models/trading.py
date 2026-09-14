from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class OrderModel(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("order_id", name="uq_orders_order_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    offset: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TradeModel(Base):
    __tablename__ = "trades"
    __table_args__ = (UniqueConstraint("trade_id", name="uq_trades_trade_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False, default="BUY")
    price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PositionModel(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    volume: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MarketDataModel(Base):
    __tablename__ = "market_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
