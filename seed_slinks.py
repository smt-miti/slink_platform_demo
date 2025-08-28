# seed_slinks.py
import argparse, time, json, math, string, random
from datetime import datetime, timezone
import psycopg2

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def base62(n: int) -> str:
    if n == 0: return "0"
    out = []
    while n > 0:
        n, r = divmod(n, 62)
        out.append(ALPHABET[r])
    return "".join(reversed(out))

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=5433)
    ap.add_argument("--db",   default="slink_db")
    ap.add_argument("--user", default="slink")
    ap.add_argument("--password", default="slink_password")
    ap.add_argument("--count", type=int, default=2000, help="rows to insert")
    ap.add_argument("--prefix", default="mk", help="code prefix")
    ap.add_argument("--start", type=int, default=1_000_000, help="counter start")
    ap.add_argument("--out", default="mock_codes.jsonl")
    args = ap.parse_args()

    start_iso = now_iso()
    t0 = time.perf_counter()
    ok = 0

    conn = psycopg2.connect(
        host=args.host, port=args.port, dbname=args.db,
        user=args.user, password=args.password
    )
    conn.autocommit = False
    cur = conn.cursor()

    # Ensure table exists (idempotent)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS slinks (
      code        VARCHAR(64) PRIMARY KEY,
      url         TEXT NOT NULL,
      alias       VARCHAR(64) UNIQUE,
      clicks      INTEGER NOT NULL DEFAULT 0,
      created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_slinks_url ON slinks (url);
    """)
    conn.commit()

    with open(args.out, "w", encoding="utf-8") as outf:
        for i in range(args.count):
            n = args.start + i
            code = f"{args.prefix}{base62(n).rjust(6, '0')}"
            url = f"https://example.com/{n}"
            try:
                cur.execute("""
                    INSERT INTO slinks(code, url, alias)
                    VALUES (%s, %s, NULL)
                    ON CONFLICT (code) DO NOTHING
                """, (code, url))
                ok += cur.rowcount  # 1 if inserted, 0 if existed
                outf.write(json.dumps({"code": code, "url": url}) + "\n")
            except Exception as e:
                conn.rollback()
            else:
                # commit in batches for speed
                if (i + 1) % 500 == 0:
                    conn.commit()
        conn.commit()

    cur.close()
    conn.close()

    dt = time.perf_counter() - t0
    end_iso = now_iso()
    print(f"START: {start_iso}")
    print(f"END:   {end_iso}")
    print(f"TOTAL: {dt:.3f} s")
    print(f"INSERTED: {ok}/{args.count} rows")
    if dt > 0:
        print(f"RPS: {ok/dt:.1f} rows/s")

if __name__ == "__main__":
    main()
