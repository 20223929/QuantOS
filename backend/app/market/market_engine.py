import asyncio
from datetime import datetime

from .tick import Tick


class MarketEngine:
    def __init__(self):
        self.running = False

    async def stream(self):
        self.running = True
        price = 3200.0

        while self.running:
            price += 0.5
            yield Tick(
                symbol="SHFE.rb2601",
                price=price,
                volume=1,
                timestamp=datetime.now(),
            )
            await asyncio.sleep(1)

    def stop(self):
        self.running = False
