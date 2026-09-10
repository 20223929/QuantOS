from dataclasses import dataclass
from datetime import datetime


@dataclass
class Tick:
    symbol: str
    price: float
    volume: int
    timestamp: datetime
