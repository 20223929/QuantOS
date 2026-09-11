from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradeRecord:
    trade_id: str
    order_id: str
    symbol: str
    volume: int
    price: float
    created_at: datetime = datetime.utcnow()
