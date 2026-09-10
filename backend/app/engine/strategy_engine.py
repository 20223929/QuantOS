class StrategyEngine:
    def __init__(self):
        self.strategies = {}

    def register(self, strategy):
        self.strategies[strategy.name] = strategy

    async def start(self, name):
        strategy = self.strategies[name]
        await strategy.start()

    async def stop(self, name):
        strategy = self.strategies[name]
        await strategy.stop()
