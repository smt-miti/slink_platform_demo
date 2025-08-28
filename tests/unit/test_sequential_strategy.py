"""
Tests for the Bitly-like SequentialStrategy.
Focus on uniqueness, padding, prefix behavior, and Base62 sanity checks.
"""
from slink_platform.manager.strategies import SequentialStrategy, _base62_encode


def test_sequential_uniqueness_and_padding():
    s = SequentialStrategy(start=1000, min_length=6)
    seen = set()
    for _ in range(5000):
        code = s.generate("https://example.com")
        assert len(code) >= 6
        assert code not in seen
        seen.add(code)


def test_sequential_prefix():
    s = SequentialStrategy(start=1000, min_length=6, prefix="ap")
    c = s.generate("x")
    assert c.startswith("ap")
    assert len(c) >= 2 + 6  # prefix + minlen


def test_base62_progression_sanity():
    assert _base62_encode(0) == "0"
    assert _base62_encode(61) == "Z"
    assert _base62_encode(62) == "10"
