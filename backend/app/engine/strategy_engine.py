from __future__ import annotations

import inspect


class StrategyEngine:
    """Manage registered strategies and their lifecycle."""

    def __init__(self):
        self.strategies = {}
        self.running: set[str] = set()

    def register(self, strategy):
        if not getattr(strategy, "name", None):
            raise ValueError("strategy must define a name")
        self.strategies[strategy.name] = strategy
        return strategy

    def list(self):
        return [{"name": name, "running": name in self.running} for name in self.strategies]

    async def start(self, name):
        strategy = self.strategies[name]
        result = strategy.start()
        if inspect.isawaitable(result):
            await result
        self.running.add(name)
        return {"name": name, "status": "started"}

    async def stop(self, name):
        strategy = self.strategies[name]
        result = strategy.stop()
        if inspect.isawaitable(result):
            await result
        self.running.discard(name)
        return {"name": name, "status": "stopped"}
