"""Strategy lifecycle runner foundation for QuantOS."""

from dataclasses import dataclass


@dataclass
class StrategyState:
    name: str
    running: bool = False


class StrategyRunner:
    def __init__(self, strategy):
        self.strategy = strategy
        self.state = StrategyState(strategy.__class__.__name__)

    def start(self):
        self.state.running = True
        if hasattr(self.strategy, "start"):
            self.strategy.start()

    def stop(self):
        self.state.running = False
        if hasattr(self.strategy, "stop"):
            self.strategy.stop()
