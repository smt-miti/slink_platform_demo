"""
NFR: redirect throughput and latency (concurrency-capable, soft by default)

How to run (opt-in):
    RUN_NFR=1 pytest tests/nfr/test_perf_redirect.py -vv

Optional thresholds (env):
    NFR_TARGET_REDIRECT_QPS=800
    NFR_TARGET_REDIRECT_P95_MS=5
    NFR_CONCURRENCY=8
    NFR_REQUESTS=5000
    RUN_NFR_STRICT=1           # only then will thresholds cause test failures

Notes:
    - Uses FastAPI TestClient (in-process). Absolute QPS varies by OS/CPU.
    - On laptops/Windows, 300–600 QPS is typical. To achieve multi-k QPS,
      run uvicorn with multiple workers & benchmark externally (k6/locust).
"""

import os
import time
import math
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient
from main import create_app

import logging

import logging
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("uvicorn").setLevel(logging.WARNING)

pytestmark = pytest.mark.nfr


def _should_run():
    return os.getenv("RUN_NFR") == "1"


@pytest.fixture(scope="function")
def client():
    # Fresh app per test for clean in-memory state
    return TestClient(create_app())


@pytest.mark.skipif(not _should_run(), reason="NFR tests are opt-in; set RUN_NFR=1 to enable")
def test_redirect_throughput_and_latency(client, capsys):
    # Seed a slink
    resp = client.post("/slink", json={"url": "https://example.com/nfr-redirect"})
    assert resp.status_code == 200
    code = resp.json()["slink"]

    # Config
    total_requests = int(os.getenv("NFR_REQUESTS", "5000"))
    concurrency = max(1, int(os.getenv("NFR_CONCURRENCY", "1")))
    per_thread = math.ceil(total_requests / concurrency)

    # Warmup to stabilize imports/JIT/caches
    for _ in range(min(200, total_requests // 10 or 1)):
        r = client.get(f"/slink/{code}", headers={"Accept": "application/json"})
        assert r.status_code == 200

    # Worker for concurrent calls
    def worker(n_times: int):
        lat = []
        for _ in range(n_times):
            s = time.perf_counter()
            r = client.get(f"/slink/{code}", headers={"Accept": "application/json"})
            e = time.perf_counter()
            assert r.status_code == 200
            lat.append((e - s) * 1000.0)
        return lat

    # Run concurrent batches
    t0 = time.perf_counter()
    latencies_ms = []
    print(f"Starting redirect NFR: {total_requests} requests @ conc {concurrency}...")
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(worker, per_thread) for _ in range(concurrency)]
        for fut in as_completed(futures):
            latencies_ms.extend(fut.result())
    t1 = time.perf_counter()

    # Trim extras if not divisible
    latencies_ms = latencies_ms[:total_requests]

    total_s = t1 - t0
    qps = len(latencies_ms) / total_s
    p95 = statistics.quantiles(latencies_ms, n=100)[94] if len(latencies_ms) >= 100 else max(latencies_ms)

    # Report
    print(
        f"\nRedirect N={len(latencies_ms)}, conc={concurrency} -> "
        f"total {total_s:.3f}s, QPS={qps:.1f}, p95={p95:.2f}ms"
    )


    with capsys.disabled():
        print(
            f"\nRedirect N={len(latencies_ms)}, conc={concurrency} -> "
            f"total {total_s:.3f}s, QPS={qps:.1f}, p95={p95:.2f}ms",
            flush=True,
        )
    

    # Thresholds (soft by default)
    strict = os.getenv("RUN_NFR_STRICT") == "1"
    qps_target = os.getenv("NFR_TARGET_REDIRECT_QPS")
    p95_target_ms = os.getenv("NFR_TARGET_REDIRECT_P95_MS")

    if strict:
        # Enforce only in strict mode (e.g., perf environment)
        if qps_target:
            assert qps >= float(qps_target), f"Redirect QPS {qps:.1f} < target {qps_target}"
        if p95_target_ms:
            assert p95 <= float(p95_target_ms), f"Redirect p95 {p95:.2f}ms > target {p95_target_ms}ms"
    else:
        # Non-strict: provide informative guidance, but don't fail the suite
        if qps_target and qps < float(qps_target):
            print(f"WARNING: Redirect QPS {qps:.1f} < target {qps_target} (non-strict mode)")
        if p95_target_ms and p95 > float(p95_target_ms):
            print(f"WARNING: Redirect p95 {p95:.2f}ms > target {p95_target_ms}ms (non-strict mode)")
