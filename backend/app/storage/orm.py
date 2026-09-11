from .database import Database
from .models.base import Base


class ORMManager:
    """ORM initialization helper."""

    def __init__(self, database: Database):
        self.database = database

    def create_tables(self):
        Base.metadata.create_all(bind=self.database.engine)
