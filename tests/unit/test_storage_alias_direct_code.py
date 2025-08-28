"""
Targeted coverage test for the direct-code branch in Storage.alias_exists.

LLM Prompt Example:
    "Provide a minimal test to exercise the early 'alias is the code'
    branch in alias_exists for full coverage."
"""

from slink_platform.storage.storage import Storage


def test_alias_exists_true_when_alias_is_code_key():
    s = Storage()
    # Save an entry where the code itself is "aliasCode" (no vanity alias field)
    assert s.save_slink("aliasCode", "https://example.com") is True

    # This should hit the early `if alias in self.slinks: return True` branch
    assert s.alias_exists("aliasCode") is True
