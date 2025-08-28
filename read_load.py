"""
read_load.py — simple async load script to follow redirects

Usage:
  python read_load.py --base http://127.0.0.1:8000 --in slinks_created.jsonl --count 15000 --concurrency 200
"""
import argparse
import asyncio
import json
import random
import time
from datetime import datetime, timezone

import httpx

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _load_codes(path):
    codes = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                c = obj.get("code")
                if c:
                    codes.append(c)
            except Exception:
                pass
    return codes

async def _hit_one(client: httpx.AsyncClient, base: str, code: str):
    try:
        r = await client.get(f"{base}/{code}", allow_redirects=False, timeout=10)
        # Expect 307 redirect, but accept any 2xx/3xx
        return 200 <= r.status_code < 400
    except Exception:
        return False

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--in", dest="codes_file", default="slinks_created.jsonl")
    parser.add_argument("--count", type=int, default=15000)
    parser.add_argument("--concurrency", type=int, default=200)
    args = parser.parse_args()

    codes = _load_codes(args.codes_file)
    if not codes:
        print(f"No codes found in {args.codes_file}. Run write_load.py first.")
        return

    start_iso = _now_iso()
    t0 = time.perf_counter()
    success = 0

    limit = httpx.Limits(max_connections=args.concurrency, max_keepalive_connections=args.concurrency)
    async with httpx.AsyncClient(limits=limit) as client:
        sem = asyncio.Semaphore(args.concurrency)

        async def _task(i):
            nonlocal success
            async with sem:
                ok = await _hit_one(client, args.base, random.choice(codes))
                if ok:
                    success += 1

        await asyncio.gather(*(_task(i) for i in range(args.count)))

    dt = time.perf_counter() - t0
    end_iso = _now_iso()
    print(f"START: {start_iso}")
    print(f"END:   {end_iso}")
    print(f"TOTAL: {dt:.3f} s")
    print(f"OPS:   reads={args.count}, ok={success}, fail={args.count - success}")
    if dt > 0:
        print(f"RPS:   {success/dt:.1f} req/s")

if __name__ == "__main__":
    asyncio.run(main())
