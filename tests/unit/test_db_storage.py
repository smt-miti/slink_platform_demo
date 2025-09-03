import pytest
from slink_platform.storage.db_storage import DBStorage
import psycopg.rows


class DummyCursor:
    def __init__(self, results=None, rowcount=1):
        # results is a list of dicts or tuples
        self._results = results or []
        self.rowcount = rowcount
        self._index = 0

    def execute(self, query, params=None):
        return True

    def fetchone(self):
        if self._results and self._index < len(self._results):
            row = self._results[self._index]
            self._index += 1
            return row
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyConnection:
    def __init__(self, results=None, rowcount=1):
        self.results = results
        self.rowcount = rowcount
        self.autocommit = True

    def cursor(self, row_factory=None):
        # If row_factory=dict_row, expect dict results
        if row_factory == psycopg.rows.dict_row:
            return DummyCursor(results=self.results, rowcount=self.rowcount)
        else:
            return DummyCursor(results=self.results, rowcount=self.rowcount)

    def close(self):
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------

def test_get_slink(monkeypatch):
    # dict_row → return dict
    row_dict = {
        "code": "abc",
        "url": "https://x.com",
        "alias": None,
        "created_at": "now",
        "status": 1,
        "click_count": 0,
    }
    conn = DummyConnection(results=[row_dict])
    monkeypatch.setattr("psycopg.connect", lambda dsn: conn)

    storage = DBStorage("fake")
    row = storage.get_slink("abc")
    assert row["code"] == "abc"
    assert row["url"] == "https://x.com"


def test_find_code_by_url(monkeypatch):
    # default cursor → return tuple
    conn = DummyConnection(results=[("abc",)])
    monkeypatch.setattr("psycopg.connect", lambda dsn: conn)

    storage = DBStorage("fake")
    code = storage.find_code_by_url("https://x.com")
    assert code == "abc"


def test_save_slink(monkeypatch):
    # Insert succeeds
    conn = DummyConnection(rowcount=1)
    monkeypatch.setattr("psycopg.connect", lambda dsn: conn)
    storage = DBStorage("fake")
    assert storage.save_slink("abc", "https://x.com") is True

    # Insert ignored (rowcount=0)
    conn = DummyConnection(rowcount=0)
    monkeypatch.setattr("psycopg.connect", lambda dsn: conn)
    storage = DBStorage("fake")
    assert storage.save_slink("abc", "https://x.com") is False


def test_increment_click(monkeypatch):
    conn = DummyConnection(rowcount=1)
    monkeypatch.setattr("psycopg.connect", lambda dsn: conn)
    storage = DBStorage("fake")
    assert storage.increment_click("abc") is True


def test_alias_exists(monkeypatch):
    # return True
    conn = DummyConnection(results=[(True,)])
    monkeypatch.setattr("psycopg.connect", lambda dsn: conn)
    storage = DBStorage("fake")
    assert storage.alias_exists("alias1") is True

    # return False
    conn = DummyConnection(results=[(False,)])
    monkeypatch.setattr("psycopg.connect", lambda dsn: conn)
    storage = DBStorage("fake")
    assert storage.alias_exists("alias1") is False


def test_delete_slink(monkeypatch):
    conn = DummyConnection(rowcount=1)
    monkeypatch.setattr("psycopg.connect", lambda dsn: conn)
    storage = DBStorage("fake")
    assert storage.delete_slink("abc") is True


def test_disable_slink(monkeypatch):
    conn = DummyConnection(rowcount=1)
    monkeypatch.setattr("psycopg.connect", lambda dsn: conn)
    storage = DBStorage("fake")
    assert storage.disable_slink("abc") is True
