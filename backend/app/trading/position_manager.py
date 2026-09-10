class PositionManager:
    def __init__(self):
        self.positions = {}

    async def update(self, symbol: str, volume: int):
        self.positions[symbol] = volume
        return self.positions[symbol]

    def get(self, symbol: str):
        return self.positions.get(symbol, 0)
