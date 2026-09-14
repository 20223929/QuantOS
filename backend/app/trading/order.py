from dataclasses import dataclass


@dataclass
class Order:
    symbol: str
    side: str
    volume: int
    price: float = 0.0
    status: str = "PENDING"
    offset: str = "OPEN"
    order_id: str | None = None
    broker_order: object | None = None
    reason: str = ""
    filled_volume: float = 0.0
