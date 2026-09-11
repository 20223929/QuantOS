from backend.app.storage.models.base import Base


def test_initial_schema_metadata_imports():
    assert Base.metadata is not None
