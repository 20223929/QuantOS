from backend.app.storage.repositories.position_repository import PositionRepository
from backend.app.storage.repositories.market_repository import MarketDataRepository


def test_position_repository_import():
    assert PositionRepository is not None


def test_market_repository_import():
    assert MarketDataRepository is not None
