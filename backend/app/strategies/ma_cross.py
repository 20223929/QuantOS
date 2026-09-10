from dataclasses import dataclass

from app.engine.base_strategy import BaseStrategy


@dataclass
class MACrossSignal:
    action: str
    price: float


class MACrossStrategy(BaseStrategy):
    """Simple MA5/MA20 cross strategy example."""

    def __init__(self):
        self.short_window = 5
        self.long_window = 20
        self.prices: list[float] = []

    def start(self):
        self.prices.clear()

    def stop(self):
        pass

    def on_bar(self, price: float):
        self.prices.append(price)

        if len(self.prices) < self.long_window:
            return None

        short_ma = sum(self.prices[-self.short_window:]) / self.short_window
        long_ma = sum(self.prices[-self.long_window:]) / self.long_window

        if short_ma > long_ma:
            return MACrossSignal(action="BUY", price=price)

        if short_ma < long_ma:
            return MACrossSignal(action="SELL", price=price)

        return None
