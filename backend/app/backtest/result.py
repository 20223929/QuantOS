from dataclasses import dataclass


@dataclass
class BacktestResult:
    trades: list
    total_return: float = 0.0
    max_drawdown: float = 0.0
    initial_capital: float = 0.0
    final_equity: float = 0.0

    def summary(self):
        return {
            "trades": len(self.trades),
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "initial_capital": self.initial_capital,
            "final_equity": self.final_equity,
        }
