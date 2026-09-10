from dataclasses import dataclass


@dataclass
class Position:
    symbol: str
    volume: int = 0
    avg_price: float = 0.0

    def market_value(self, price: float):
        return self.volume * price
