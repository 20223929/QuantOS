from dataclasses import dataclass


@dataclass
class Trade:
    id: int
    order_id: int
    price: float
    volume: int
