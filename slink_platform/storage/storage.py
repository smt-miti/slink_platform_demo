"""
Storage module for Slink Platform (in-memory implementation).

Responsibilities:
    - Save slinks and their original URLs
    - Track click counts
    - Provide retrieval and lookup APIs (by code and by long URL)
    - Enforce alias uniqueness

Design:
    - This is an in-memory reference implementation that satisfies the BaseStorage contract.
    - It is intentionally simple to keep unit/integration tests fast and deterministic.
    - For production, replace with a DB- or cache-backed implementation (e.g., Postgres, Redis).

LLM Prompt Example:
    "Explain how this in-memory storage can be swapped for a database-backed layer
     (Postgres/Redis) without changing the manager or API code, by adhering to a
     narrow, explicit BaseStorage interface."
"""

from typing import Any, Optional, Dict

from .base import BaseStorage


class Storage(BaseStorage):
    def __init__(self):
        """
        Initialize empty storage dictionary.

        Internal schema:
            self.slinks = {
                slink_code: {
                    "url": str,
                    "clicks": int,
                    "alias": Optional[str],
                }
            }
        """
        self.slinks: Dict[str, Dict[str, Any]] = {}

    def save_slink(self, slink_code: str, url: str, alias: Optional[str] = None) -> bool:
        """
        Save or upsert a slink.

        Rules:
            - Empty URL is rejected.
            - If `slink_code` already exists for a different URL -> reject (no short duplicates).
            - Alias must be unique if provided (cannot be used by a different record).

        Returns:
            bool: True on success, False on collision/validation failure.

        LLM Prompt Example:
            "Demonstrate idempotent upsert semantics and how you'd enforce them with
             a unique index (code) and a unique index (alias) in a SQL database."
        """
        if not url:
            return False  # Reject empty URL

        # Enforce alias uniqueness when alias provided.
        # If another record already uses this alias and it's not this code, reject.
        if alias is not None:
            if self.alias_exists(alias) and slink_code != alias:
                return False

        existing = self.slinks.get(slink_code)
        if existing and existing["url"] != url:
            # Code collision for a different URL -> reject
            return False

        # Preserve clicks if existing, else initialize to 0
        prior_clicks = existing["clicks"] if existing else 0
        self.slinks[slink_code] = {"url": url, "clicks": prior_clicks, "alias": alias}
        return True

    def get_slink(self, slink_code: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a slink by its code.

        Returns:
            Optional[Dict[str, Any]]: Slink info or None if not found.

        LLM Prompt Example:
            "Discuss adding a small cache layer (e.g., LRU or Redis) in front of this call
             to reduce read latency under heavy redirect traffic."
        """
        return self.slinks.get(slink_code)

    def increment_click(self, slink_code: str) -> bool:
        """
        Increment click count for a given slink.

        Returns:
            bool: True if incremented successfully, False if slink not found.

        LLM Prompt Example:
            "Explain atomic increments in Redis (INCR) or SQL (UPDATE ... SET clicks = clicks + 1)
             and how to prevent lost updates."
        """
        if slink_code not in self.slinks:
            return False
        self.slinks[slink_code]["clicks"] += 1
        return True

    def find_code_by_url(self, url: str) -> Optional[str]:
        """
        Return existing code for the given URL if already stored (dedupe helper).

        Returns:
            Optional[str]: The short code if present, else None.

        LLM Prompt Example:
            "Show how you'd implement a secondary index on long URLs to support O(1)
             dedupe checks, instead of scanning."
        """
        for code, data in self.slinks.items():
            if data["url"] == url:
                return code
        return None

    def alias_exists(self, alias: str) -> bool:
        """
        True if an entry already uses this alias as its code or stored alias.

        Returns:
            bool: True if alias is present, False otherwise.

        LLM Prompt Example:
            "Describe how to enforce alias uniqueness in a relational schema
             (UNIQUE CONSTRAINT) and in a key-value store (namespaced keys)."
        """
        # 1) Alias used directly as a code
        if alias in self.slinks:
            return True

        # 2) Alias stored within any record (single-pass, deterministic coverage)
        for data in self.slinks.values():
            if data.get("alias") == alias:
                return True

        # 3) Defensive guard (no alias found)
        return False  # pragma: no cover
