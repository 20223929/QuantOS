from dataclasses import dataclass

from app.engine.base_strategy import BaseStrategy


@dataclass
class MACrossSignal:
    action: str
    price: float


class MACrossStrategy(BaseStrategy):
    """MA5/MA20 crossover strategy producing signals only on a crossover."""

    name = "ma_cross"

    def __init__(self, short_window: int = 5, long_window: int = 20):
        if short_window <= 0 or long_window <= short_window:
            raise ValueError("long_window must be greater than short_window > 0")
        self.short_window = short_window
        self.long_window = long_window
        self.prices: list[float] = []
        self.previous_relation: int | None = None

    def start(self):
        self.prices.clear()
        self.previous_relation = None

    def stop(self):
        return None

    def on_bar(self, bar):
        price = float(bar.get("close", 0)) if isinstance(bar, dict) else float(getattr(bar, "close", bar))
        self.prices.append(price)
        if len(self.prices) < self.long_window:
            return None

        short_ma = sum(self.prices[-self.short_window:]) / self.short_window
        long_ma = sum(self.prices[-self.long_window:]) / self.long_window
        relation = 1 if short_ma > long_ma else -1 if short_ma < long_ma else 0

        signal = None
        if self.previous_relation is not None:
            if relation > 0 and self.previous_relation <= 0:
                signal = MACrossSignal("BUY", price)
            elif relation < 0 and self.previous_relation >= 0:
                signal = MACrossSignal("SELL", price)
        self.previous_relation = relation
        return signal
