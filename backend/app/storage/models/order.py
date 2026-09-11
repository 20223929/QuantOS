from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional


@dataclass
class OrderRecord:
    order_id: str
    symbol: str
    side: str
    volume: int
    price: Optional[float] = None
    status: str = "PENDING"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
