from dataclasses import dataclass
from typing import Any


@dataclass
class OrderEvent:
    order_id: str
    status: str
    payload: dict[str, Any] | None = None


@dataclass
class TradeEvent:
    order_id: str
    symbol: str
    volume: int
    price: float


@dataclass
class PositionEvent:
    symbol: str
    volume: int
    avg_price: float
