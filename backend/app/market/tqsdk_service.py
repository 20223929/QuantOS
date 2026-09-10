"""TqSdk market service facade for QuantOS.

Keeps TqSdk integration isolated from strategy and backtest engines.
"""

from app.adapters.tqsdk_adapter import TqSdkAdapter


class TqSdkMarketService:
    def __init__(self):
        self.adapter = TqSdkAdapter()

    async def start(self):
        await self.adapter.connect()

    async def subscribe(self, symbol: str):
        return await self.adapter.subscribe(symbol)

    async def tick(self, symbol: str):
        return await self.adapter.get_tick(symbol)
