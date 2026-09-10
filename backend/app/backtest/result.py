from dataclasses import dataclass


@dataclass
class BacktestResult:
    trades: list
    total_return: float = 0.0
    max_drawdown: float = 0.0

    def summary(self):
        return {
            "trades": len(self.trades),
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
        }
