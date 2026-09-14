from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .result import BacktestResult


@dataclass
class _Position:
    direction: int = 0
    volume: int = 0
    entry_price: float = 0.0


class BacktestEngine:
    """Deterministic single-symbol event-driven backtest engine."""

    def __init__(self, strategy, initial_capital: float = 100_000.0, contract_multiplier: float = 1.0):
        self.strategy = strategy
        self.initial_capital = float(initial_capital)
        self.contract_multiplier = float(contract_multiplier)
        self.trades: list[dict[str, Any]] = []

    @staticmethod
    def _close_price(bar: Any) -> float:
        return float(bar.get("close", 0)) if isinstance(bar, dict) else float(getattr(bar, "close", bar))

    def run(self, bars) -> BacktestResult:
        bars = list(bars)
        self.trades.clear()
        position = _Position()
        realized = 0.0
        equity_curve = [self.initial_capital]

        start = getattr(self.strategy, "start", None)
        if callable(start):
            started = start()
            if hasattr(started, "__await__"):
                raise TypeError("backtest strategy start() must be synchronous")

        for bar in bars:
            price = self._close_price(bar)
            signal = self.strategy.on_bar(bar)
            if isinstance(signal, dict):
                action = str(signal.get("action", "")).upper()
                signal_price = float(signal.get("price", price))
            else:
                action = str(getattr(signal, "action", "")).upper()
                signal_price = float(getattr(signal, "price", price))

            if action not in {"BUY", "SELL"}:
                unrealized = position.direction * position.volume * (price - position.entry_price) * self.contract_multiplier if position.direction else 0.0
                equity_curve.append(self.initial_capital + realized + unrealized)
                continue

            target = 1 if action == "BUY" else -1
            if position.direction != target:
                if position.direction:
                    pnl = position.direction * position.volume * (signal_price - position.entry_price) * self.contract_multiplier
                    realized += pnl
                    self.trades.append({"action": "SELL" if position.direction == 1 else "BUY", "side": "CLOSE", "price": signal_price, "volume": position.volume, "pnl": pnl})
                position = _Position(direction=target, volume=1, entry_price=signal_price)
                self.trades.append({"action": action, "side": "OPEN", "price": signal_price, "volume": 1, "pnl": 0.0})

            unrealized = position.direction * position.volume * (price - position.entry_price) * self.contract_multiplier
            equity_curve.append(self.initial_capital + realized + unrealized)

        if position.direction and bars:
            final_price = self._close_price(bars[-1])
            pnl = position.direction * position.volume * (final_price - position.entry_price) * self.contract_multiplier
            realized += pnl
            self.trades.append({"action": "SELL" if position.direction == 1 else "BUY", "side": "CLOSE_EOD", "price": final_price, "volume": position.volume, "pnl": pnl})
            equity_curve.append(self.initial_capital + realized)

        peak = self.initial_capital
        max_drawdown = 0.0
        for equity in equity_curve:
            peak = max(peak, equity)
            if peak > 0:
                max_drawdown = max(max_drawdown, (peak - equity) / peak)

        return BacktestResult(
            trades=self.trades.copy(),
            total_return=(realized / self.initial_capital) if self.initial_capital else 0.0,
            max_drawdown=max_drawdown,
            initial_capital=self.initial_capital,
            final_equity=self.initial_capital + realized,
        )
