"""
NFR: creation throughput and latency

How to run (opt-in):
    RUN_NFR=1 pytest tests/nfr/test_perf_create.py -vv
Optional thresholds:
    NFR_TARGET_CREATE_QPS=1000     # assert create QPS >= 1000 (example)
    NFR_TARGET_CREATE_P95_MS=5     # assert p95 latency per create <= 5 ms

Notes:
    - Uses the manager fixture (in-memory) for deterministic measurements.
    - Does not assert unless env vars are set (skips otherwise).
    - For real-world runs, prefer pytest-benchmark/Locust/k6; this keeps zero extra deps.
"""

import os
import time
import statistics
import pytest

from slink_platform.manager.slink_manager import SlinkManager
from slink_platform.storage.storage import Storage
from slink_platform.analytics.analytics import Analytics


pytestmark = pytest.mark.nfr


def _should_run():
    return os.getenv("RUN_NFR") == "1"


@pytest.mark.skipif(not _should_run(), reason="NFR tests are opt-in; set RUN_NFR=1 to enable")
def test_create_throughput_and_latency(capsys):
    # Fresh in-memory components (don’t reuse global fixtures to avoid cross-test state)
    manager = SlinkManager(storage=Storage(), analytics=Analytics())

    n = 2000  # create N distinct URLs; keep modest for local/laptop runs
    latencies_ms = []

    t0 = time.perf_counter()
    for i in range(n):
        url = f"https://example.com/resource/{i}"
        s = time.perf_counter()
        code = manager.create_slink(url)
        e = time.perf_counter()
        assert code  # sanity
        latencies_ms.append((e - s) * 1000.0)
    t1 = time.perf_counter()

    total_s = t1 - t0
    qps = n / total_s
    p95 = statistics.quantiles(latencies_ms, n=100)[94] if len(latencies_ms) >= 100 else max(latencies_ms)

    # Optional asserts
    qps_target = os.getenv("NFR_TARGET_CREATE_QPS")
    p95_target_ms = os.getenv("NFR_TARGET_CREATE_P95_MS")

    if qps_target:
        assert qps >= float(qps_target), f"Create QPS {qps:.1f} < target {qps_target}"
    if p95_target_ms:
        assert p95 <= float(p95_target_ms), f"Create p95 {p95:.2f}ms > target {p95_target_ms}ms"

    # Always emit human-friendly metrics in assertion-free mode
    print(f"\nCreate N={n} -> total {total_s:.3f}s, QPS={qps:.1f}, p95={p95:.2f}ms")

            # Always emit human-friendly metrics
    with capsys.disabled():    # <-- force print to terminal
        print(f"\nCreate N={n} -> total {total_s:.3f}s, QPS={qps:.1f}, p95={p95:.2f}ms", flush=True)

        if qps_target and qps < float(qps_target):
            print(f"WARNING: Create QPS {qps:.1f} < target {qps_target} (non-strict mode)", flush=True)
        if p95_target_ms and p95 > float(p95_target_ms):
            print(f"WARNING: Create p95 {p95:.2f}ms > target {p95_target_ms}ms (non-strict mode)", flush=True)
