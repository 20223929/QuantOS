from __future__ import annotations


class PerformanceMetrics:
    """Calculate common backtest statistics from normalized trades."""

    def __init__(self, trades=None, initial_capital: float = 100_000.0, final_equity: float | None = None, max_drawdown: float = 0.0):
        self.trades = trades or []
        self.initial_capital = float(initial_capital)
        self.final_equity = final_equity
        self.max_drawdown = float(max_drawdown)

    def summary(self):
        pnl_values = [float(t.get("pnl", 0.0)) for t in self.trades if t.get("side", "").startswith("CLOSE")]
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p < 0]
        realized = sum(pnl_values)
        return {
            "trade_count": len(pnl_values),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": (len(wins) / len(pnl_values)) if pnl_values else 0.0,
            "realized_pnl": realized,
            "profit_factor": (sum(wins) / abs(sum(losses))) if losses else (float("inf") if wins else 0.0),
            "return": ((self.final_equity - self.initial_capital) / self.initial_capital) if self.final_equity is not None and self.initial_capital else 0.0,
            "max_drawdown": self.max_drawdown,
        }


class PerformanceAnalyzer(PerformanceMetrics):
    """Backward-compatible alias for performance analysis."""
