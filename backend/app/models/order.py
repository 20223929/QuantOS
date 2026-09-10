from dataclasses import dataclass


@dataclass
class Order:
    id: int
    symbol: str
    side: str
    volume: int
    price: float
