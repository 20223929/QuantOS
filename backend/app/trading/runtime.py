from __future__ import annotations

import asyncio
import inspect
from typing import Any

from app.trading.order import Order


class StrategyRuntime:
    """Drive a strategy from market bars into the trading execution engine."""

    def __init__(self, market_adapter, strategy, execution_engine, symbol: str, duration_seconds: int = 60, data_length: int = 200):
        self.market_adapter = market_adapter
        self.strategy = strategy
        self.execution_engine = execution_engine
        self.symbol = symbol
        self.duration_seconds = duration_seconds
        self.data_length = data_length
        self.running = False
        self.task: asyncio.Task | None = None
        self.last_bar_datetime: Any = None
        self.last_signal: Any = None

    async def start(self):
        if self.running:
            return
        await self.market_adapter.connect()
        result = self.strategy.start()
        if inspect.isawaitable(result):
            await result
        self.running = True
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        self.running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.task = None
        result = self.strategy.stop()
        if inspect.isawaitable(result):
            await result

    async def run(self):
        while self.running:
            frame = await self.market_adapter.get_bars(self.symbol, self.duration_seconds, self.data_length)
            if len(frame) == 0:
                await asyncio.sleep(0.5)
                continue

            bar = frame.iloc[-1]
            bar_datetime = getattr(bar, "datetime", None)
            if bar_datetime is not None and bar_datetime == self.last_bar_datetime:
                await asyncio.to_thread(self.market_adapter.api.wait_update)
                continue

            self.last_bar_datetime = bar_datetime
            payload = bar.to_dict() if hasattr(bar, "to_dict") else bar
            signal = self.strategy.on_bar(payload)
            if signal:
                action = str(getattr(signal, "action", "")).upper()
                price = float(getattr(signal, "price", payload.get("close", 0) if isinstance(payload, dict) else 0))
                order = Order(symbol=self.symbol, side=action, volume=1, price=price, offset="OPEN")
                self.last_signal = self.execution_engine.execute(order)

            await asyncio.to_thread(self.market_adapter.api.wait_update)

    def status(self) -> dict:
        return {
            "symbol": self.symbol,
            "running": self.running,
            "strategy": getattr(self.strategy, "name", self.strategy.__class__.__name__),
            "last_bar_datetime": self.last_bar_datetime,
            "last_signal": getattr(self.last_signal, "message", None),
        }
