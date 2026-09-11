from dataclasses import dataclass
from datetime import datetime


@dataclass
class PositionRecord:
    symbol: str
    volume: int
    avg_price: float
    updated_at: datetime = datetime.utcnow()
