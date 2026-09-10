class PerformanceMetrics:
    """Backtest performance metrics calculator."""

    def __init__(self, trades=None):
        self.trades = trades or []

    def summary(self):
        return {
            "trade_count": len(self.trades)
        }


class PerformanceAnalyzer:
    """Calculate basic strategy metrics."""

    def __init__(self, trades):
        self.trades = trades

    def summary(self):
        return {
            "trade_count": len(self.trades)
        }
