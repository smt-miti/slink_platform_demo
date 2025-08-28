"""
NFR: concurrency/idempotency for create_slink

Goal:
    Simulate many creation attempts for the same URL and ensure:
      - Manager returns a stable code (idempotency)
      - Storage contains a single mapping for that URL (no duplicates)

How to run (opt-in):
    RUN_NFR=1 pytest tests/nfr/test_concurrency_idempotency.py -vv

Notes:
    - Uses a simple loop for determinism; true parallelism would require a
      thread-safe storage backend. This still validates the idempotent contract.
"""

import os
import pytest

from slink_platform.manager.slink_manager import SlinkManager
from slink_platform.storage.storage import Storage
from slink_platform.analytics.analytics import Analytics

pytestmark = pytest.mark.nfr


def _should_run():
    return os.getenv("RUN_NFR") == "1"


@pytest.mark.skipif(not _should_run(), reason="NFR tests are opt-in; set RUN_NFR=1 to enable")
def test_idempotent_on_repeated_creates_same_url():
    storage = Storage()
    manager = SlinkManager(storage=storage, analytics=Analytics())

    url = "https://example.com/idempotent"
    codes = set()

    N = 5000
    for _ in range(N):
        codes.add(manager.create_slink(url))

    # Must be a single code across all attempts
    assert len(codes) == 1
    only_code = next(iter(codes))
    record = storage.get_slink(only_code)
    assert record is not None and record["url"] == url
