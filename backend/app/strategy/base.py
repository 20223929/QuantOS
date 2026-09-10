from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Unified strategy lifecycle for backtest and live trading."""

    def __init__(self, name: str):
        self.name = name

    def on_init(self):
        pass

    @abstractmethod
    def on_bar(self, bar):
        pass

    def on_tick(self, tick):
        pass

    def on_order(self, order):
        pass

    def on_trade(self, trade):
        pass

    def on_stop(self):
        pass
