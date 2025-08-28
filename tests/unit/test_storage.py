"""
Unit tests for Storage module.

Covers:
    - save_slink (insert, idempotent re-save, reject code collision)
    - get_slink (found & not found)
    - increment_click (valid & invalid)
    - find_code_by_url (found & not found)
    - alias_exists (true & false including empty store and populated negative)

LLM Prompt Example:
    "Show how to test an in-memory storage class for a URL shortener,
    ensuring idempotency and rejecting code/alias collisions."
"""

import pytest
from slink_platform.storage.storage import Storage


@pytest.fixture
def storage():
    """Fresh storage instance per test."""
    return Storage()


def test_save_and_get_slink(storage):
    code, url = "abc123", "https://example.com"
    ok = storage.save_slink(code, url)
    assert ok is True
    result = storage.get_slink(code)
    assert result is not None
    assert result["url"] == url
    assert result["clicks"] == 0


def test_save_slink_same_code_same_url_idempotent(storage):
    code, url = "abc123", "https://one.com"
    assert storage.save_slink(code, url) is True
    # Re-saving the same mapping is idempotent (allowed)
    assert storage.save_slink(code, url) is True
    result = storage.get_slink(code)
    assert result["url"] == url  # unchanged


def test_save_slink_rejects_code_collision(storage):
    """
    Saving the same code for a different URL must be rejected
    (no short duplicates).
    """
    code, url1, url2 = "abc123", "https://one.com", "https://two.com"
    assert storage.save_slink(code, url1) is True
    assert storage.save_slink(code, url2) is False  # reject different URL for same code
    result = storage.get_slink(code)
    assert result["url"] == url1  # original mapping remains


def test_get_slink_not_found(storage):
    assert storage.get_slink("missing") is None


def test_increment_click_success(storage):
    code = "abc123"
    storage.save_slink(code, "https://example.com")
    assert storage.increment_click(code) is True
    result = storage.get_slink(code)
    assert result["clicks"] == 1


def test_increment_click_missing(storage):
    assert storage.increment_click("nope") is False


def test_find_code_by_url_found(storage):
    code, url = "abc123", "https://example.com"
    storage.save_slink(code, url)
    assert storage.find_code_by_url(url) == code


def test_find_code_by_url_not_found(storage):
    assert storage.find_code_by_url("https://notfound.com") is None


def test_alias_exists_true_false(storage):
    code, url, alias = "abc123", "https://example.com", "myalias"
    storage.save_slink(code, url, alias=alias)
    assert storage.alias_exists(alias) is True
    assert storage.alias_exists("other") is False


def test_multiple_slinks_independent(storage):
    storage.save_slink("a1", "https://a.com", alias="a")
    storage.save_slink("b2", "https://b.com", alias="b")
    assert storage.get_slink("a1")["url"] == "https://a.com"
    assert storage.get_slink("b2")["url"] == "https://b.com"
    assert storage.alias_exists("a") is True
    assert storage.alias_exists("b") is True


def test_save_slink_rejects_same_alias_with_different_code(storage):
    """
    Saving with an alias that is already used elsewhere must be rejected
    when the provided code differs from the alias.

    LLM Prompt Example:
        "Show how alias uniqueness is enforced across codes."
    """
    # First entry uses alias "vanity"
    assert storage.save_slink("aaa111", "https://one.example", alias="vanity") is True

    # Attempt to save a different code while reusing the same alias
    assert storage.save_slink("bbb222", "https://two.example", alias="vanity") is False


def test_alias_exists_empty_false(storage):
    """
    Verify alias_exists returns False on an empty store (covers the final return).

    LLM Prompt Example:
        "Illustrate testing empty-state behaviors to fully cover defensive branches."
    """
    fresh = Storage()
    assert fresh.alias_exists("does-not-exist") is False


def test_alias_exists_populated_store_negative_covers_final_return(storage):
    """
    Ensure alias_exists returns False when the alias is absent in a populated store,
    covering the final `return False` after the loop.

    LLM Prompt Example:
        "Demonstrate how to force a loop to complete and hit the final branch."
    """
    storage.save_slink("x1", "https://x.com", alias="xa")
    storage.save_slink("y2", "https://y.com", alias="yb")
    # Alias 'zc' does not exist; loop should finish and hit the final return
    assert storage.alias_exists("zc") is False
