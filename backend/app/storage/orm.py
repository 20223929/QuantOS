from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models.base import Base
from .models.outbox import ExecutionOutboxModel
from .models.trading import MarketDataModel, OrderModel, PositionModel, TradeModel


class ORMManager:
    """SQLAlchemy ORM initialization and session helper."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)

    def session(self):
        return self.SessionLocal()
