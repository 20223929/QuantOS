class BacktestEngine:
    """Event driven backtest engine."""

    def __init__(self, strategy):
        self.strategy = strategy
        self.trades = []

    def run(self, bars):
        for bar in bars:
            signal = self.strategy.on_bar(bar)
            if signal:
                self.trades.append({
                    "signal": signal,
                    "price": bar.close
                })

        return self.trades
