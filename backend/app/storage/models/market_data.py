from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class MarketDataRecord:
    symbol: str
    price: float
    volume: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
