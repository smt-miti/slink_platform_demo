"""
Unit tests for Analytics module.

Covers:
    - log_click for valid/invalid clicks
    - source counting and multiple sources
    - summary with and without only_valid=True
    - empty state

LLM Prompt Example:
    "Show how to test analytics for a URL shortener ensuring
    valid/invalid click tracking, source aggregation, and summaries."
"""

import pytest
from slink_platform.analytics.analytics import Analytics


@pytest.fixture
def analytics():
    """Fresh Analytics per test."""
    return Analytics()


def test_log_click_valid_increments_counts(analytics):
    code = "abc123"
    analytics.log_click(code, source="api", valid=True)
    summary = analytics.summary()
    assert code in summary
    s = summary[code]
    assert s["total_clicks"] == 1
    assert s["valid_clicks"] == 1
    assert "last_click" in s
    assert s["sources"]["api"] == 1


def test_log_click_invalid_tracked_but_not_valid(analytics):
    code = "abc123"
    analytics.log_click(code, source="browser", valid=False)
    summary = analytics.summary()
    s = summary[code]
    assert s["total_clicks"] == 1
    assert s["valid_clicks"] == 0
    assert s["sources"]["browser"] == 1


def test_multiple_sources_aggregated(analytics):
    code = "abc123"
    analytics.log_click(code, source="api", valid=True)
    analytics.log_click(code, source="browser", valid=True)
    analytics.log_click(code, source="api", valid=True)  # second API click
    s = analytics.summary()[code]
    assert s["total_clicks"] == 3
    assert s["valid_clicks"] == 3
    assert s["sources"]["api"] == 2
    assert s["sources"]["browser"] == 1


def test_summary_only_valid_filters_out_invalid(analytics):
    code = "abc123"
    analytics.log_click(code, source="api", valid=False)
    full_summary = analytics.summary()
    filtered_summary = analytics.summary(only_valid=True)

    assert code in full_summary
    # Excluded in only_valid because no valid clicks
    assert code not in filtered_summary


def test_summary_empty_returns_empty_dict(analytics):
    assert analytics.summary() == {}
    assert analytics.summary(only_valid=True) == {}
