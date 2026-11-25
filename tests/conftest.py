import pytest


@pytest.fixture
def memory_db(monkeypatch):
    """Keep every service on the same fresh database for this test."""
    import mongomock
    from backend.app import database

    client = mongomock.MongoClient()
    monkeypatch.setattr(database, "_client", client)
    monkeypatch.setenv("MONGODB_DB_NAME", "integration_test")
    return database.get_db()
