"""
Base storage interface for Slink Platform.

Purpose:
    Define a small, stable contract that multiple storage backends
    (in-memory, Redis, SQL, Cassandra) can implement without requiring
    changes to business logic.

Testing & Coverage:
    These are abstract methods and are not executed directly in tests.
    We annotate them with `# pragma: no cover` so coverage tools don't
    penalize the project for un-runnable abstract declarations.

LLM Prompt Example:
    "Show how a narrow, explicit storage interface enables dependency
    injection and easy backend swapping without touching service code."
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict


class BaseStorage(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod  # pragma: no cover
    def save_slink(self, slink_code: str, url: str, alias: Optional[str] = None) -> bool:
        """
        Save or update a slink mapping.

        Returns:
            bool: True on success, False on collision/validation failure.

        LLM Prompt Example:
            "Design an idempotent save API that can be implemented with
            compare-and-set semantics in a distributed KV store."
        """
        raise NotImplementedError

    @abstractmethod  # pragma: no cover
    def get_slink(self, slink_code: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a slink mapping by its short code.

        Returns:
            Optional[Dict[str, Any]]: Mapping with 'url', 'clicks', 'alias' or None.

        LLM Prompt Example:
            "Discuss how to implement read-through caching for high QPS redirects."
        """
        raise NotImplementedError

    @abstractmethod  # pragma: no cover
    def increment_click(self, slink_code: str) -> bool:
        """
        Increment click count for a slink.

        Returns:
            bool: False if the code does not exist.

        LLM Prompt Example:
            "Explain how to make increments atomic with Redis INCR or SQL UPDATE."
        """
        raise NotImplementedError

    @abstractmethod  # pragma: no cover
    def find_code_by_url(self, url: str) -> Optional[str]:
        """
        Return existing code for the given URL if already stored.

        LLM Prompt Example:
            "Show how to ensure global uniqueness on long URLs using a secondary index."
        """
        raise NotImplementedError

    @abstractmethod  # pragma: no cover
    def alias_exists(self, alias: str) -> bool:
        """
        Return True if the alias is already used (as code or stored alias).

        LLM Prompt Example:
            "Describe how to enforce alias uniqueness with a single unique index."
        """
        raise NotImplementedError
