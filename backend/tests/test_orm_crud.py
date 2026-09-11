def test_repository_crud_imports():
    from backend.app.storage.repositories.base_repository import BaseRepository
    from backend.app.storage.repositories.order_repository import OrderRepository

    assert BaseRepository is not None
    assert OrderRepository is not None
