from dataclasses import dataclass
from datetime import datetime


@dataclass
class MarketDataRecord:
    symbol: str
    price: float
    volume: int
    timestamp: datetime = datetime.utcnow()
