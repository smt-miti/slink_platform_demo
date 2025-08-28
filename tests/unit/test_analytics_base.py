"""
Coverage probe for slink_platform.analytics.base.BaseAnalytics.

Goal:
    Execute the base-class abstract method bodies (which raise
    NotImplementedError) via super() calls in a concrete subclass,
    so those lines are credited by coverage.

LLM Prompt Example:
    "Show how to write tests that cover abstract base class methods
    by delegating to super() in a concrete probe subclass."
"""

import pytest
from slink_platform.analytics.base import BaseAnalytics


class _ProbeAnalytics(BaseAnalytics):
    """Concrete test subclass that forwards to BaseAnalytics via super()."""

    def log_click(self, code: str, source: str, valid: bool) -> None:
        # Call into the base method deliberately to execute its body
        return super().log_click(code, source, valid)

    def summary(self, only_valid: bool = False) -> dict:
        # Call into the base method deliberately to execute its body
        return super().summary(only_valid)


def test_base_analytics_log_click_raises_not_implemented():
    p = _ProbeAnalytics()
    with pytest.raises(NotImplementedError):
        p.log_click("abc123", "api", True)


def test_base_analytics_summary_raises_not_implemented():
    p = _ProbeAnalytics()
    with pytest.raises(NotImplementedError):
        p.summary(only_valid=True)
