def test_alembic_setup_imports():
    from backend.app.storage.migrations import env

    assert env.target_metadata is not None
