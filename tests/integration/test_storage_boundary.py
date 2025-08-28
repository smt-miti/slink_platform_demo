"""
Boundary integration tests for Storage backends.

Note: Empty URL validation is a **manager** concern; the raw storage layer may accept empty strings
(especially DB, where URL column is NOT NULL but empty string is valid). Hence we skip that case for DB.
"""

import os
import pytest

from slink_platform.storage.storage_factory import get_storage

@pytest.fixture(params=["memory"] + (["postgres"] if os.getenv("SLINK_DB_DSN") else []))
def storage(request):
    backend = request.param
    if backend == "postgres":
        os.environ.setdefault("SLINK_STORAGE_BACKEND", "postgres")
    else:
        os.environ["SLINK_STORAGE_BACKEND"] = "memory"
    return get_storage()

def test_increment_nonexistent_click(storage):
    # Should not raise; DB returns False, memory is no-op.
    assert storage.increment_click("nonexistent") in (False, None)

@pytest.mark.parametrize("backend", ["memory", "postgres"])
def test_save_empty_url_behavior_documented(backend):
    """
    Document behavior instead of enforcing: storage layer is dumb by design.
    Manager validates URLs; storage persists bytes.
    - memory backend returns False on empty url (by implementation choice)
    - postgres backend may accept empty string (it's NOT NULL, but empty is allowed)
    """
    if backend == "postgres" and not os.getenv("SLINK_DB_DSN"):
        pytest.skip("DB not configured")
    os.environ["SLINK_STORAGE_BACKEND"] = backend
    storage = get_storage()
    result = storage.save_slink("empty1", "")
    if backend == "memory":
        assert result is False
    else:
        # Postgres path: we don't assert, just ensure it doesn't explode.
        assert result in (True, False)
