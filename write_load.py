"""
write_load.py — simple async load script to create shortlinks

Usage:
  python write_load.py --base http://127.0.0.1:8000 --count 2000 --concurrency 100 --out slinks_created.jsonl
"""
import argparse
import asyncio
import json
import random
import string
import time
from datetime import datetime, timezone

import httpx

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _rand_host():
    tlds = ["com", "net", "org", "io", "ai"]
    names = ["example", "sample", "demo", "test", "alpha", "beta", "gamma"]
    return f"{random.choice(names)}.{random.choice(tlds)}"

def _rand_path(n=6):
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))

async def _create_one(client: httpx.AsyncClient, base: str, out_file, idx: int):
    url = f"https://{_rand_host()}/{_rand_path(8)}?q={idx}"
    payload = {"url": url}
    try:
        r = await client.post(f"{base}/slink", json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        code = data.get("code")
        if code and out_file:
            out_file.write(json.dumps({"code": code, "url": url}) + "\n")
        return True
    except Exception:
        return False

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--concurrency", type=int, default=100)
    parser.add_argument("--out", default="slinks_created.jsonl")
    args = parser.parse_args()

    start_iso = _now_iso()
    t0 = time.perf_counter()
    success = 0

    limit = httpx.Limits(max_connections=args.concurrency, max_keepalive_connections=args.concurrency)
    # IMPORTANT: file uses normal "with"; client uses "async with" separately
    with open(args.out, "w", encoding="utf-8") as out_f:
        async with httpx.AsyncClient(limits=limit) as client:
            sem = asyncio.Semaphore(args.concurrency)

            async def _task(i):
                nonlocal success
                async with sem:
                    ok = await _create_one(client, args.base, out_f, i)
                    if ok:
                        success += 1

            await asyncio.gather(*(_task(i) for i in range(args.count)))

    dt = time.perf_counter() - t0
    end_iso = _now_iso()
    print(f"START: {start_iso}")
    print(f"END:   {end_iso}")
    print(f"TOTAL: {dt:.3f} s")
    print(f"OPS:   writes={args.count}, ok={success}, fail={args.count - success}")
    if dt > 0:
        print(f"TPS:   {success/dt:.1f} req/s")

if __name__ == "__main__":
    asyncio.run(main())
