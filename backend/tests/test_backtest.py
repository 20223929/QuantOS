from types import SimpleNamespace

from app.backtest.engine import BacktestEngine
from app.strategies.ma_cross import MACrossStrategy


def test_ma_cross_emits_on_crossover_only():
    strategy = MACrossStrategy(2, 4)
    values = [1, 1, 1, 1, 3, 3, 1, 1]
    signals = [strategy.on_bar(SimpleNamespace(close=value)) for value in values]
    actions = [signal.action for signal in signals if signal]
    assert actions == ["BUY", "SELL"]


def test_backtest_calculates_return_and_drawdown():
    strategy = MACrossStrategy(2, 4)
    bars = [SimpleNamespace(close=value) for value in [1, 1, 1, 1, 3, 3, 1, 1]]
    result = BacktestEngine(strategy, initial_capital=100.0).run(bars)
    assert result.final_equity == 98.0
    assert result.total_return == -0.02
    assert len(result.trades) == 4
    assert result.max_drawdown > 0
