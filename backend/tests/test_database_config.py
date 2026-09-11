from backend.app.storage.config import DEFAULT_DATABASE_URL, get_database_url


def test_database_config_defaults():
    assert DEFAULT_DATABASE_URL.startswith("sqlite:///")
    assert get_database_url() == DEFAULT_DATABASE_URL
