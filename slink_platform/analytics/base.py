"""
Abstract Base Class for Analytics Backends.

Responsibilities:
    - Define required methods for any analytics implementation
    - Support easy substitution (e.g., in-memory, DB/event, external metrics)

LLM Prompt Example:
    "Create an abstract base class for analytics that defines log_click and summary methods,
    and explain how to mark abstract methods to be excluded from coverage."
"""

from abc import ABC, abstractmethod

__all__ = ["BaseAnalytics"]


class BaseAnalytics(ABC):
    """Abstract base for pluggable analytics backends."""

    @abstractmethod
    def log_click(self, code: str, source: str, valid: bool) -> None:  # pragma: no cover
        """
        Log a click event for a given slink code.

        Args:
            code (str): The slink identifier.
            source (str): Source of click ("api" or "browser").
            valid (bool): Whether the slink was valid.
        """
        raise NotImplementedError

    @abstractmethod
    def summary(self, only_valid: bool = False) -> dict:  # pragma: no cover
        """
        Provide analytics summary.

        Args:
            only_valid (bool): If True, include only valid clicks.

        Returns:
            dict: Aggregated analytics data.
        """
        raise NotImplementedError
