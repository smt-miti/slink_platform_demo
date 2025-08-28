"""
Boundary tests for Analytics module in Slink Platform.

Responsibilities:
    - Test edge cases for click logging
    - Test handling of non-existent slinks
    - Test summary behavior with no clicks

LLM Prompt Example:
    "Demonstrate how to write boundary tests for Analytics module
    including invalid slinks and filtering by validity."
"""

import pytest
from slink_platform.analytics.analytics import Analytics

@pytest.fixture
def analytics():
    """Fixture to provide a fresh Analytics instance for each test."""
    return Analytics()

def test_log_click_nonexistent_slink(analytics):
    """
    Test logging a click for a non-existent slink.
    
    - Should not raise errors.
    - Should correctly mark the click as invalid.
    """
    slink_code = "nonexist"
    source = "api"
    analytics.log_click(slink_code, source=source, valid=False)

    clicks = analytics.get_clicks(slink_code)
    assert len(clicks) == 1
    assert clicks[0]["source"] == source
    assert clicks[0]["valid"] is False

def test_summary_no_clicks(analytics):
    """
    Test summary when no clicks exist.
    
    - Summary should return an empty dictionary.
    """
    summary = analytics.summary()
    assert isinstance(summary, dict)
    assert summary == {}

def test_log_and_filter_valid_clicks(analytics):
    """
    Test logging both valid and invalid clicks and filtering.
    
    - Only valid clicks should be returned when requested.
    """
    valid_slink = "valid123"
    invalid_slink = "invalid123"
    
    analytics.log_click(valid_slink, source="browser", valid=True)
    analytics.log_click(valid_slink, source="api", valid=False)
    analytics.log_click(invalid_slink, source="api", valid=False)

    # All clicks for valid_slink
    all_clicks = analytics.get_clicks(valid_slink)
    assert len(all_clicks) == 2

    # Only valid clicks for valid_slink
    valid_clicks = analytics.get_clicks(valid_slink, only_valid=True)
    assert len(valid_clicks) == 1
    assert valid_clicks[0]["valid"] is True
    assert valid_clicks[0]["source"] == "browser"

    # Only valid clicks for invalid_slink should be empty
    filtered_clicks = analytics.get_clicks(invalid_slink, only_valid=True)
    assert filtered_clicks == []
