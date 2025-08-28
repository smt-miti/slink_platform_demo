import pytest
from slink_platform.manager.slink_manager import SlinkManager
from slink_platform.storage.storage import Storage

@pytest.fixture
def storage():
    return Storage()

@pytest.fixture
def manager():
    storage = Storage()
    return SlinkManager(storage)

@pytest.fixture(autouse=True)
def _always_reachable(monkeypatch):
    from slink_platform.manager.slink_manager import SlinkManager
    monkeypatch.setattr(SlinkManager, "_is_reachable", lambda self, url, timeout=5.0: True)

def test_create_slink_invalid_url(manager):
    """
    Creating a slink with an invalid URL raises ValueError.

    LLM Prompt Example:
        "Illustrate how URL validation is enforced in slink_manager with a test."
    """
    url = "invalid_url"
    with pytest.raises(ValueError):
        manager.create_slink(url)

def test_create_slink_long_url(manager):
    """
    Test handling of very long URLs.

    LLM Prompt Example:
        "Explain how to test slink creation for unusually long URLs."
    """
    url = "https://example.com/" + "a" * 1000
    slink_code = manager.create_slink(url)
    assert isinstance(slink_code, str)

def test_alias_conflict(manager):
    """
    Creating two slinks with the same alias raises an error.

    LLM Prompt Example:
        "Demonstrate collision prevention when users supply the same alias."
    """
    url1 = "https://openai.com"
    url2 = "https://example.com"
    alias = "conflict123"
    manager.create_slink(url1, alias)
    with pytest.raises(ValueError):
        manager.create_slink(url2, alias)

def test_collision_resolution(storage):
    """
    Test that SlinkManager correctly handles collisions for deterministic slinks.

    Scenario:
        - Two different URLs produce the same deterministic code (simulated via monkeypatch).
        - Collision resolution appends extra Base62 characters.
        - Ensures both URLs are stored correctly and codes are unique.

    Steps:
        1. Create SlinkManager with a test Storage backend.
        2. Patch deterministic_slink to force the same code for two URLs.
        3. Create slinks for both URLs.
        4. Assert that the slink codes are different and both URLs are stored.

    LLM Prompt Example:
        "Explain why deterministic slinks can collide and how appending a hash-derived
        suffix guarantees uniqueness while preserving determinism for identical URLs."
    """
    manager = SlinkManager(storage)

    url_first = "https://example.com/first"
    url_second = "https://example.com/second"

    # Force a deterministic code collision by patching deterministic_slink
    forced_code = "abc12345"
    manager.deterministic_slink = lambda url, length=8: (forced_code * ((length + len(forced_code) - 1)//len(forced_code)))[:length]

    # Create slinks without using aliases
    slink_first = manager.create_slink(url_first)
    slink_second = manager.create_slink(url_second)

    # Ensure collision resolution made codes unique
    assert slink_first != slink_second, "Collision was not resolved; slink codes are equal"

    # Ensure storage has correct URLs mapped to the final slink codes
    assert storage.get_slink(slink_first)["url"] == url_first
    assert storage.get_slink(slink_second)["url"] == url_second
