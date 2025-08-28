# read_db_load.py
import argparse, json, random, time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_codes(path):
    codes = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                c = obj.get("code")
                if c: codes.append(c)
            except Exception:
                pass
    return codes

def one_read(conn_params, code):
    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        cur.execute("SELECT url FROM slinks WHERE code=%s", (code,))
        _ = cur.fetchone()  # ignore
        cur.close()
        conn.close()
        return True
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=5433)
    ap.add_argument("--db",   default="slink_db")
    ap.add_argument("--user", default="slink")
    ap.add_argument("--password", default="slink_password")
    ap.add_argument("--in", dest="codes_file", default="mock_codes.jsonl")
    ap.add_argument("--count", type=int, default=15000, help="number of reads")
    ap.add_argument("--threads", type=int, default=32, help="parallel threads")
    args = ap.parse_args()

    codes = load_codes(args.codes_file)
    if not codes:
        print(f"No codes found in {args.codes_file}. Run seed_slinks.py first.")
        return

    conn_params = dict(host=args.host, port=args.port, dbname=args.db,
                       user=args.user, password=args.password)

    start_iso = now_iso()
    t0 = time.perf_counter()
    ok = 0

    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = []
        for i in range(args.count):
            futures.append(ex.submit(one_read, conn_params, random.choice(codes)))
        for f in as_completed(futures):
            ok += 1 if f.result() else 0

    dt = time.perf_counter() - t0
    end_iso = now_iso()
    print(f"START: {start_iso}")
    print(f"END:   {end_iso}")
    print(f"TOTAL: {dt:.3f} s")
    print(f"OPS:   reads={args.count}, ok={ok}, fail={args.count - ok}")
    if dt > 0:
        print(f"RPS:   {ok/dt:.1f} reads/s")

if __name__ == "__main__":
    main()
