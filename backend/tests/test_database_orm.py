def test_orm_imports():
    from backend.app.storage.models.base import Base
    from backend.app.storage.orm import ORMManager

    assert Base is not None
    assert ORMManager is not None
