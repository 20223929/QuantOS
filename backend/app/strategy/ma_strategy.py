from .base import BaseStrategy


class MAStrategy(BaseStrategy):
    """Simple MA trend strategy example."""

    def __init__(self, short_window=5, long_window=20):
        super().__init__("MA Strategy")
        self.short_window = short_window
        self.long_window = long_window
        self.closes = []

    def on_bar(self, bar):
        self.closes.append(bar.close)

        if len(self.closes) < self.long_window:
            return None

        short = sum(self.closes[-self.short_window:]) / self.short_window
        long = sum(self.closes[-self.long_window:]) / self.long_window

        if short > long:
            return "BUY"
        return "SELL"
