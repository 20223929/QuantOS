from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class PositionRecord:
    symbol: str
    volume: int
    avg_price: float
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
