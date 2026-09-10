class SubscriptionManager:
    def __init__(self):
        self.symbols = set()

    async def add(self, symbol: str):
        self.symbols.add(symbol)

    async def remove(self, symbol: str):
        self.symbols.discard(symbol)
