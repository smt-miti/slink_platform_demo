"""
Integration tests for Storage backends (in-memory and Postgres).

These tests parameterize over available backends:
- Always "memory"
- "postgres" only if SLINK_DB_DSN is set (and SLINK_STORAGE_BACKEND optionally)

Best practice:
- Reuse the BaseStorage contract across backends.
- Normalize click count field differences (in-memory: 'clicks', DB: 'click_count').
"""

import os
import pytest

from slink_platform.storage.storage_factory import get_storage

def available_backends():
    backends = ["memory"]
    if os.getenv("SLINK_DB_DSN"):
        backends.append("postgres")
    return backends

@pytest.fixture(params=available_backends())
def storage(request):
    backend = request.param
    if backend == "postgres":
        os.environ.setdefault("SLINK_STORAGE_BACKEND", "postgres")
    else:
        os.environ["SLINK_STORAGE_BACKEND"] = "memory"
    return get_storage()

def _get_clicks(row: dict) -> int:
    if "clicks" in row:
        return int(row["clicks"])
    if "click_count" in row:
        return int(row["click_count"])
    return 0

def test_save_and_get_slink(storage):
    code, url = "abc123", "https://openai.com"
    assert storage.save_slink(code, url) is True
    row = storage.get_slink(code)
    assert row is not None
    assert row["url"] == url
    assert _get_clicks(row) == 0
    assert row.get("alias") in (None, "")

def test_collision_on_save(storage):
    code, url1, url2 = "abc123", "https://openai.com", "https://example.com"
    storage.save_slink(code, url1)
    assert storage.save_slink(code, url2) is False

def test_increment_click(storage):
    code, url = "xyz789", "https://openai.com"
    storage.save_slink(code, url)
    assert storage.increment_click(code) in (True, None)
    storage.increment_click(code)
    row = storage.get_slink(code)
    assert _get_clicks(row) >= 2
