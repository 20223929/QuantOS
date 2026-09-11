from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class TradeRecord:
    trade_id: str
    order_id: str
    symbol: str
    volume: int
    price: float
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
