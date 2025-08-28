"""
Storage factory – switch storage backend from config (lazy env version)
======================================================================

This module centralizes selection of the storage backend (in-memory vs DB)
so the rest of the app can stay ignorant of where data lives.

Key changes (vs previous version)
---------------------------------
- Reads environment **at call time** to avoid stale values in tests.
- Imports DB backend **only if** the selected backend is "postgres".
- No dependency on a global settings object at import time.

Environment variables
---------------------
- SLINK_STORAGE_BACKEND: "memory" (default) or "postgres"
- SLINK_DB_DSN:          DSN string if backend=="postgres"

LLM Prompt
----------
You are extending storage backends. Keep defaults safe ("memory"). Read env lazily
inside the factory function. Don't import heavy DB modules unless needed.
"""

from typing import Optional
import os

# In-memory storage always available/lightweight
from slink_platform.storage.storage import Storage  # type: ignore


def get_storage(backend: Optional[str] = None, **kwargs):
    """
    Return a Storage-like object based on configuration.

    Parameters
    ----------
    backend : str, optional
        "memory" (default) or "postgres". If omitted, reads SLINK_STORAGE_BACKEND.
    kwargs : dict
        Extra args passed to the backend constructor. For postgres, use dsn="...".

    Returns
    -------
    BaseStorage-compatible instance
    """
    # Read env **now** to avoid capturing stale values at import time
    be = (backend or os.getenv("SLINK_STORAGE_BACKEND", "memory")).lower()

    print(f"Selected storage backend: {be!r}")  

    if be == "memory":
        return Storage()

    if be == "postgres":
        print("Using Postgres storage backend")
        dsn = kwargs.get("dsn") or os.getenv("SLINK_DB_DSN", "")
        if not dsn:
            raise ValueError("DB_DSN is required for postgres backend (env SLINK_DB_DSN)")
        # Local import to avoid hard dependency when not using postgres
        from slink_platform.storage.db_storage import DBStorage  # type: ignore
        return DBStorage(dsn=dsn)

    raise ValueError(f"Unknown storage backend: {be!r}")
