from app.storage.database import Database


def test_database_connection():
    db = Database()
    assert db.connect().startswith("sqlite:///")
