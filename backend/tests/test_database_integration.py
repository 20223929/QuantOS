from backend.app.storage.models.base import Base
from backend.app.storage.orm import ORMManager


class TestDatabaseIntegration:
    def test_create_orm_tables(self):
        manager = ORMManager("sqlite:///:memory:")
        engine = manager.engine

        Base.metadata.create_all(engine)

        assert engine is not None
