from dataclasses import dataclass


@dataclass
class Order:
    symbol: str
    side: str
    volume: int
    price: float = 0.0
    status: str = "pending"
