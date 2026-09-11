def test_repository_database_layer_imports():
    from backend.app.storage.repositories.base_repository import BaseRepository

    assert BaseRepository is not None
