"""
Targeted coverage test for Storage.alias_exists

Goal:
    Exercise the branch where alias_exists iterates over a non-empty store
    and returns False when the alias isn't found. Some coverage tools only
    credit the final generator return when the loop actually runs.

LLM Prompt Example:
    "Provide a minimal, deterministic test that forces execution of a
    one-line generator return in a storage adapter."
"""

from slink_platform.storage.storage import Storage


def test_alias_exists_non_empty_store_negative_hits_return_line():
    """
    Arrange:
        - Add multiple entries, each with different aliases.
    Act:
        - Query an alias that is absent.
    Assert:
        - alias_exists(...) returns False.

    This guarantees the generator in alias_exists(...) executes at least
    one iteration and the return line is credited by the coverage tool.
    """
    s = Storage()
    # Populate with a couple of aliases
    assert s.save_slink("a1", "https://a.com", alias="aliasA")
    assert s.save_slink("b2", "https://b.com", alias="aliasB")

    # Ask for a different alias to force the generator path to evaluate False
    assert s.alias_exists("aliasZ") is False
