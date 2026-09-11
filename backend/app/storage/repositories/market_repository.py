from backend.app.storage.repository import Repository


class MarketDataRepository(Repository):
    """Repository for market data persistence."""

    def save_market_data(self, market_data):
        return self.save(market_data)
