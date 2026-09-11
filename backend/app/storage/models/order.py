from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class OrderRecord:
    order_id: str
    symbol: str
    side: str
    volume: int
    price: Optional[float] = None
    status: str = "PENDING"
    created_at: datetime = datetime.utcnow()
