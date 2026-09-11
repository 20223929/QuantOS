from sqlalchemy import create_engine

from .models.base import Base


class ORMManager:
    """ORM initialization helper."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
