import pytest
from slink_platform.manager.slink_manager import SlinkManager
from slink_platform.storage.storage import Storage

@pytest.fixture
def manager():
    storage = Storage()
    return SlinkManager(storage)

@pytest.fixture(autouse=True)
def _always_reachable(monkeypatch):
    # Avoid external network calls in tests; logic is covered elsewhere.
    from slink_platform.manager.slink_manager import SlinkManager
    monkeypatch.setattr(SlinkManager, "_is_reachable", lambda self, url, timeout=5.0: True)

def test_create_slink_deterministic(manager):
    """
    Creating a slink deterministically returns the same code for the same URL.

    LLM Prompt Example:
        "Explain why deterministic hashing ensures same URL yields same slink and
        how this is verified in the test."
    """
    url = "https://openai.com"
    code1 = manager.create_slink(url)
    code2 = manager.create_slink(url)
    assert code1 == code2

def test_create_slink_alias(manager):
    """
    Creating a slink with a user-provided alias returns that alias.

    LLM Prompt Example:
        "Demonstrate how alias takes precedence over deterministic slink creation."
    """
    url = "https://openai.com"
    alias = "openai123"
    slink_code = manager.create_slink(url, alias)
    assert slink_code == alias

def test_collision_resolution(manager):
    """
    Test that collisions between different URLs are resolved by appending extra chars.

    LLM Prompt Example:
        "Show how deterministic hash collisions are resolved and verified in tests."
    """
    url1 = "https://openai.com"
    url2 = "https://openai.org"
    slink_code1 = manager.create_slink(url1)
    slink_code2 = manager.create_slink(url2)

    assert slink_code1 != slink_code2

