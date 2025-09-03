"""
DBStorage – PostgreSQL-backed storage for Slink Platform
=======================================================

This module provides a production-friendly storage backend that persists slinks in PostgreSQL.
It adheres to the same contract as the in-memory Storage (see `storage.py`) by implementing
the `BaseStorage` interface, so you can switch backends without touching business logic.

LLM Prompt (for future maintainers)
-----------------------------------
You are an assistant improving or extending a PostgreSQL storage adapter for a URL shortener.
Keep the public API identical to `BaseStorage`. Prioritize correctness, idempotence, and
safe SQL. Avoid breaking changes in method signatures. Prefer parameterized queries, small
transactions per call, and `ON CONFLICT` upserts. Add comprehensive docstrings and examples.

Key Design Points
-----------------
- **Idempotence**: Creating the same long URL returns the same code (enforced by manager),
  while the DB layer ensures code-level uniqueness (`PRIMARY KEY(code)`), alias uniqueness,
  and (optionally) long-URL uniqueness.
- **Upserts**: Uses `ON CONFLICT (code) DO NOTHING` for `save_slink`. Additional uniqueness
  rules can be enforced by schema (e.g., `UNIQUE(url)`), but we keep writes simple.
- **Connections**: Uses `psycopg` 3 for short-lived connections per call. For higher throughput,
  consider a connection pool (psycopg.ConnectionPool) later.
- **Portability**: The SQL in this module is Postgres-flavored (ON CONFLICT). MySQL variants
  would use `INSERT IGNORE` / `ON DUPLICATE KEY UPDATE code=code` instead.

Schema Expectations
-------------------
See `schema.sql` at repo root for the canonical DDL. Required tables/constraints:
- `slinks(code PRIMARY KEY, url NOT NULL, alias UNIQUE NULLS NOT DISTINCT, created_at, status)`
- Optional partial index: `CREATE UNIQUE INDEX ux_slinks_alias ON slinks(alias) WHERE alias IS NOT NULL;`
- Optional: `UNIQUE(url)` for idempotent long-url mapping.

Example
-------
>>> storage = DBStorage(dsn="postgresql://slink:slink@127.0.0.1:5432/slink")
>>> storage.save_slink("AbC12345", "https://example.com", alias=None)
True
>>> storage.get_slink("AbC12345")['url']
'https://example.com'

"""

from typing import Optional, Dict, Any
import contextlib

import psycopg
import psycopg.rows

from .base import BaseStorage


class DBStorage(BaseStorage):
    """PostgreSQL implementation of the Slink storage contract.

    Parameters
    ----------
    dsn : str
        Psycopg DSN, e.g. "postgresql://user:pass@host:5432/dbname"

    Notes
    -----
    - Each method opens a short connection. For higher QPS, replace `_conn()` with a pool.
    - All queries are parameterized to avoid injection and support plan caching.
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    # ---- Internal helpers -------------------------------------------------

    @contextlib.contextmanager
    def _conn(self):
        """Context manager creating a psycopg connection."""
        print("Opening new database connection...",self.dsn)
        con = psycopg.connect(self.dsn)
        con.autocommit = True  # default; override in methods if needed
        try:
            yield con
        finally:
            con.close()

    # ---- Contract methods -------------------------------------------------

    def get_slink(self, code: str) -> Optional[Dict[str, Any]]:
        """Return a slink row by code or None if not found."""
        with self._conn() as con, con.cursor(row_factory=psycopg.rows.dict_row) as cur:
            print(f"DBStorage.connection_detail: connection={con}")
            cur.execute("SELECT code, url, alias, created_at, status, COALESCE(click_count,0) AS click_count FROM slinks WHERE code = %s", (code,))
            row = cur.fetchone()
            return dict(row) if row else None

    def find_code_by_url(self, url: str) -> Optional[str]:
        """Return code if there is a row mapped to the given url, else None.

        Implementation detail: relies on a plain SELECT; add a UNIQUE(url) index
        if you want DB-level enforcement and fast lookups.
        """
        with self._conn() as con, con.cursor() as cur:
            cur.execute("SELECT code FROM slinks WHERE url = %s", (url,))
            row = cur.fetchone()
            return row[0] if row else None

    def save_slink(self, code: str, url: str, alias: Optional[str] = None) -> bool:
        """Persist a (code, url, alias) triple if the code is not taken.

        Returns
        -------
        bool
            True if a new row was inserted, False if the code already existed.

        Notes
        -----
        - Uses ON CONFLICT (code) DO NOTHING.
        - If you want alias uniqueness at DB level, add a UNIQUE constraint on alias
          (nullable). Manager logic should also check alias collisions before calling save.
        """
        print(f"DBStorage.save_slink: code={code}, url={url}, alias={alias}")
        with self._conn() as con, con.cursor() as cur:
            print("Inserting slink into database...")
            con.autocommit = True  # ensure immediate commit
            res = cur.execute(
                """
                INSERT INTO slinks (code, url, alias)
                VALUES (%s, %s, %s)
                ON CONFLICT (code) DO NOTHING
                """,
                (code, url, alias),
            )
            print("Insert executed.",res)
            print(f"Rows affected: {cur.rowcount}")
            return cur.rowcount == 1

    def increment_click(self, code: str) -> bool:
        """Increment click counter for a slink.

        Returns True if the row exists and was updated.

        Implementation detail:
            Expects a `click_count` column in `slinks` (BIGINT DEFAULT 0).
            If your schema doesn't include it, add it or route clicks to analytics backend.
        """
        with self._conn() as con, con.cursor() as cur:
            cur.execute("UPDATE slinks SET click_count = COALESCE(click_count,0) + 1 WHERE code = %s", (code,))
            return cur.rowcount == 1

    def alias_exists(self, alias: str) -> bool:
        """Return True if the alias is already used (as code or stored alias)."""
        with self._conn() as con, con.cursor() as cur:
            cur.execute("SELECT EXISTS (SELECT 1 FROM slinks WHERE code = %s OR alias = %s)", (alias, alias))
            row = cur.fetchone()
            return bool(row[0]) if row else False

    # ---- Optional helpers -------------------------------------------------

    def delete_slink(self, code: str) -> bool:
        """Delete a slink by code. Returns True if a row was removed."""
        with self._conn() as con, con.cursor() as cur:
            cur.execute("DELETE FROM slinks WHERE code = %s", (code,))
            return cur.rowcount == 1

    def disable_slink(self, code: str) -> bool:
        """Soft-disable a slink (status=0)."""
        with self._conn() as con, con.cursor() as cur:
            cur.execute("UPDATE slinks SET status = 0 WHERE code = %s", (code,))
            return cur.rowcount == 1
