"""
Unit tests for slink_platform.manager.strategies.

LLM Prompt Example:
    "Demonstrate tests that validate deterministic and random strategies,
    and explicitly cover Base62's zero edge-case."
"""

import re
from slink_platform.manager.strategies import DeterministicStrategy, RandomStrategy

BASE62_PATTERN = re.compile(r"^[0-9a-zA-Z]+$")


def test_deterministic_strategy_stability_and_charset():
    s = DeterministicStrategy()
    url = "https://example.com/path?q=1"

    c0 = s.generate(url, counter=0)
    c0b = s.generate(url, counter=0)
    c1 = s.generate(url, counter=1)

    assert c0 == c0b  # stable for same inputs
    assert c1 != c0   # counter changes output
    assert BASE62_PATTERN.match(c0)
    assert BASE62_PATTERN.match(c1)


def test_random_strategy_length_charset_and_diversity():
    r = RandomStrategy()
    samples = [r.generate("ignored") for _ in range(200)]
    assert all(len(x) == 6 and BASE62_PATTERN.match(x) for x in samples)
    assert len(set(samples)) > 20  # basic diversity check


def test_base62_zero_edge_case():
    """Cover the 'num == 0' branch inside DeterministicStrategy._base62_encode."""
    s = DeterministicStrategy()
    assert s._base62_encode(0) == "0"
