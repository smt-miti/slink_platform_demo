from __future__ import annotations
"""
Strategies for short-code generation in slink_platform.

Provided strategies:
- SHA256Strategy: Deterministic SHA-256(url|counter) -> Base62 -> truncate to L
- HMACSHA256Strategy: Keyed deterministic HMAC-SHA256(secret, url|counter) -> Base62 -> truncate to L
- RandomStrategy: Random Base62 of length L (default 6 when not provided)
- SequentialStrategy (NEW): Bitly-like monotonically increasing integer -> Base62, with optional left-pad and prefix

Common helpers:
- _base62_encode: Non-negative integer -> Base62 string
- _safe_len: Resolve/normalize desired code length from argument/config (clamped to [4, 32])

Configuration (via slink_platform.config.settings or env-like attributes):
- CODE_STRATEGY: "sha256" (default), "hmac-sha256", "random", "sequential"
- CODE_LENGTH: Default length for deterministic strategies (default 8; clamped 4..32)
- CODE_SECRET: Secret for HMACSHA256Strategy
- SEQ_START: Starting integer for SequentialStrategy (default 3_500_000)
- CODE_MIN_LENGTH: Minimum visible length for SequentialStrategy (default 6)
- SHARD_PREFIX: Optional string prefix for SequentialStrategy (e.g., "ap")

Notes:
- RandomStrategy uses length=6 by default when length is omitted (to preserve historical tests),
Best practices:
- Centralize all configuration in `slink_platform.config.settings`.
- Keep strategies stateless except for SequentialStrategy's in-memory counter.
- Prefer deterministic strategies for idempotency; use sequential for shortest codes.

  while deterministic strategies defer to CODE_LENGTH (default 8).
- SequentialStrategy ignores "length" for growth (codes grow by natural Base62 expansion),
  but enforces CODE_MIN_LENGTH via left-padding to avoid overly short, guessable codes.
"""

import hashlib
import hmac
import random
import threading
import itertools
from dataclasses import dataclass
from typing import Dict, Optional, Type
from abc import ABC, abstractmethod

# Config import with safe fallback for bare test contexts
try:
    from slink_platform.config import settings
except Exception:
    class _Fallback:
        CODE_STRATEGY = "sha256"
        CODE_LENGTH = 8
        CODE_SECRET = ""
        SEQ_START = 3_500_000
        CODE_MIN_LENGTH = 6
        SHARD_PREFIX = ""
    settings = _Fallback()

_BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BASE62_BASE = len(_BASE62_ALPHABET)


def _base62_encode(num: int) -> str:
    """
    Convert a non-negative integer to a Base62 string using the global alphabet.
    0 -> "0", 61 -> "Z", 62 -> "10"
    """
    if num < 0:
        raise ValueError("num must be non-negative")
    if num == 0:
        return "0"
    out = []
    while num > 0:
        num, rem = divmod(num, _BASE62_BASE)
        out.append(_BASE62_ALPHABET[rem])
    return "".join(reversed(out))


def _safe_len(length: Optional[int]) -> int:
    """
    Resolve desired code length from arg or config, clamped to [4, 32].
    Deterministic strategies use config default (CODE_LENGTH=8 unless overridden).
    """
    L = int(length) if length is not None else int(getattr(settings, "CODE_LENGTH", 8))
    return max(4, min(32, L))


class BaseStrategy(ABC):
    """Abstract base for code generation strategies."""
    @abstractmethod
    def generate(self, url: str, *, length: Optional[int] = None, counter: int = 0) -> str:
        """
        Generate a short code for the given URL.
        - length: desired truncated length (where applicable)
        - counter: used by deterministic strategies to rehash on rare collision
        """
        raise NotImplementedError


@dataclass(frozen=True)
class SHA256Strategy(BaseStrategy):
    """Deterministic SHA-256 -> Base62 -> truncate strategy."""
    def generate(self, url: str, *, length: Optional[int] = None, counter: int = 0) -> str:
        L = _safe_len(length)
        payload = url if counter == 0 else f"{url}|{counter}"
        digest = hashlib.sha256(payload.encode("utf-8")).digest()
        num = int.from_bytes(digest, "big", signed=False)
        return _base62_encode(num)[:L]


# Backward-compat alias (if older tests reference DeterministicStrategy)
class DeterministicStrategy(SHA256Strategy):
    """Alias for original deterministic strategy; exposes _base62_encode for some tests."""
    def _base62_encode(self, num: int) -> str:  # pragma: no cover
        return _base62_encode(num)


@dataclass(frozen=True)
class HMACSHA256Strategy(BaseStrategy):
    """Keyed deterministic HMAC-SHA256(secret, url|counter) -> Base62 -> truncate."""
    secret: str
    def generate(self, url: str, *, length: Optional[int] = None, counter: int = 0) -> str:
        L = _safe_len(length)
        payload = url if counter == 0 else f"{url}|{counter}"
        digest = hmac.new(self.secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
        num = int.from_bytes(digest, "big", signed=False)
        return _base62_encode(num)[:L]


@dataclass(frozen=True)
class RandomStrategy(BaseStrategy):
    """
    Random Base62 codes; rely on storage-level uniqueness (unique index + retry).
    Note: When 'length' is None, default to 6 to preserve historical tests/behavior.
    """
    def generate(self, url: str, *, length: Optional[int] = None, counter: int = 0) -> str:
        L = _safe_len(length) if length is not None else 6
        rng = random.SystemRandom()
        return "".join(rng.choice(_BASE62_ALPHABET) for _ in range(L))


@dataclass
class SequentialStrategy(BaseStrategy):
    """
    Bitly-like sequential strategy (NEW):
    - Maintains a process-local monotonically increasing counter
    - Encodes next integer to Base62
    - Enforces minimum visible length via left-padding (e.g., "000abc")
    - Optionally prepends a shard/region prefix (e.g., "ap000abc")

    Properties:
    - Collision-free within a single process (no retries required)
    - Shortest practical codes; length grows only when the counter exceeds 62^L - 1
    - Stateless across restarts unless the start value is persisted externally

    Configuration:
    - SEQ_START (int): starting integer (default 3_500_000 to avoid ultra-short codes)
    - CODE_MIN_LENGTH (int): minimum visible length (default 6)
    - SHARD_PREFIX (str): optional prefix (default "")
    """
    start: int = 3_500_000
    min_length: int = 6
    prefix: str = ""
    _lock: threading.Lock = threading.Lock()
    _counter: itertools.count = None  # type: ignore

    def __post_init__(self):
        # Instantiate the counter at runtime so forked processes do not share the same iterator object.
        object.__setattr__(self, "_counter", itertools.count(self.start))

    def generate(self, url: str, *, length: Optional[int] = None, counter: int = 0) -> str:
        # length is intentionally ignored; sequential growth is natural; min_length is enforced.
        with self._lock:
            n = next(self._counter)
        code = _base62_encode(n)
        if len(code) < self.min_length:
            code = code.rjust(self.min_length, "0")
        if self.prefix:
            code = f"{self.prefix}{code}"
        return code


# Strategy registry and factory
STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "sha256": SHA256Strategy,
    "sha-256": SHA256Strategy,
    "deterministic": SHA256Strategy,
    "hmac": HMACSHA256Strategy,
    "hmac-sha256": HMACSHA256Strategy,
    "random": RandomStrategy,
    "rand": RandomStrategy,
    "sequential": SequentialStrategy,
    "seq": SequentialStrategy,
    "bitly": SequentialStrategy,
}


def get_strategy_from_config(name: Optional[str] = None) -> BaseStrategy:
    """
    Resolve the active strategy from parameter or settings.CODE_STRATEGY.
    Returns a constructed strategy instance, performing any required wiring (e.g., secret for HMAC).
    """
    key = (name or getattr(settings, "CODE_STRATEGY", "sha256") or "sha256").strip().lower()
    cls = STRATEGY_REGISTRY.get(key) or STRATEGY_REGISTRY["sha256"]
    print(f"Using code strategy: {key} -> {cls.__name__}")

    if cls is HMACSHA256Strategy:
        secret = getattr(settings, "CODE_SECRET", "")
        return HMACSHA256Strategy(secret=secret)
    if cls is SequentialStrategy:
        start = int(getattr(settings, "SEQ_START", 3_500_000))
        min_len = int(getattr(settings, "CODE_MIN_LENGTH", 6))
        prefix = str(getattr(settings, "SHARD_PREFIX", ""))
        return SequentialStrategy(start=start, min_length=min_len, prefix=prefix)
    return cls()  # type: ignore[call-arg]


def code_strategy(url: str, length: Optional[int] = None, counter: int = 0) -> str:
    """
    Facade used by the rest of the app.
    Calls the strategy selected by settings.CODE_STRATEGY (or default).
    """
    strategy = get_strategy_from_config()
    return strategy.generate(url, length=length, counter=counter)
