"""
Runtime configuration for Slink Platform
=======================================

Simple settings module that reads from environment variables (only here),
and exposes a stable `settings` object for the rest of the codebase.
Avoid reading env vars anywhere else—import from this module instead.

Storage
-------
- SLINK_STORAGE_BACKEND : "memory" (default) or "postgres"
- SLINK_DB_DSN          : DSN like "postgresql://user:pass@host:5432/db"

Short-code strategy
-------------------
- SLINK_CODE_STRATEGY     : one of "sha256" (default), "hmac-sha256", "random", "sequential"
- SLINK_CODE_LENGTH       : int length; default 8; clamped to [4, 32] (for deterministic/hash strategies)
- SLINK_CODE_SECRET       : secret for "hmac-sha256"

Sequential strategy (Bitly-style) knobs
---------------------------------------
- SLINK_SEQ_START         : starting integer for the counter (default 3500000)
- SLINK_CODE_MIN_LENGTH   : minimum visible length (default 6; enforced via left-pad)
- SLINK_SHARD_PREFIX      : optional string prefix (e.g., "ap")
"""

import os


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except Exception:
        return default


class _Settings:
    # -------- Storage --------
    STORAGE_BACKEND: str = os.getenv("SLINK_STORAGE_BACKEND", "memory").strip().lower()
    DB_DSN: str = os.getenv("SLINK_DB_DSN", "")

    # -------- Short-code generation (common) --------
    #CODE_STRATEGY: str = os.getenv("SLINK_CODE_STRATEGY", "sequential").strip().lower()
    CODE_STRATEGY: str = os.getenv("SLINK_CODE_STRATEGY", "sha256").strip().lower()


    # For deterministic/hash strategies; RandomStrategy may override its own default when length=None
    _len_raw = _get_int("SLINK_CODE_LENGTH", 8)
    CODE_LENGTH: int = max(4, min(32, _len_raw))

    CODE_SECRET: str = os.getenv("SLINK_CODE_SECRET", "")

    # -------- Sequential strategy (Bitly-style) --------
    # High start to avoid ultra-short public codes in demos
    SEQ_START: int = _get_int("SLINK_SEQ_START", 3_500_000)

    # Minimum visible length (left-padded if the Base62 code is shorter)
    CODE_MIN_LENGTH: int = max(4, min(32, _get_int("SLINK_CODE_MIN_LENGTH", 6)))

    # Optional shard/region prefix (e.g., "ap")
    SHARD_PREFIX: str = os.getenv("SLINK_SHARD_PREFIX", "")


settings = _Settings()
