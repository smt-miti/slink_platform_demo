import os
import importlib
import pytest

def reload_factory():
    import slink_platform.storage.storage_factory as factory
    importlib.reload(factory)
    return factory

def test_get_storage_memory(monkeypatch):
    monkeypatch.setenv("SLINK_STORAGE_BACKEND", "memory")
    factory = reload_factory()
    storage = factory.get_storage()
    from slink_platform.storage.storage import Storage
    assert isinstance(storage, Storage)

def test_get_storage_postgres_without_dsn(monkeypatch):
    monkeypatch.setenv("SLINK_STORAGE_BACKEND", "postgres")
    monkeypatch.delenv("SLINK_DB_DSN", raising=False)
    factory = reload_factory()
    with pytest.raises(ValueError, match="DB_DSN is required"):
        factory.get_storage()

def test_get_storage_postgres_with_dsn(monkeypatch):
    monkeypatch.setenv("SLINK_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("SLINK_DB_DSN", "postgresql://user:pass@localhost:5432/db")
    factory = reload_factory()
    from slink_platform.storage.db_storage import DBStorage
    storage = factory.get_storage()
    assert isinstance(storage, DBStorage)

def test_get_storage_unknown_backend(monkeypatch):
    monkeypatch.setenv("SLINK_STORAGE_BACKEND", "nosuch")
    factory = reload_factory()
    with pytest.raises(ValueError, match="Unknown storage backend"):
        factory.get_storage()
