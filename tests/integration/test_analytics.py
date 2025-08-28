import pytest
from slink_platform.analytics.analytics import Analytics

def test_log_click_and_summary(analytics):
    """
    Test logging multiple clicks and verifying summary.

    LLM Prompt Example:
        "Show how to extend this test to validate daily and weekly aggregation of clicks."
    """
    analytics.log_click("abc123", source="browser")
    analytics.log_click("abc123", source="api")
    
    clicks = analytics.get_clicks("abc123")
    assert len(clicks) == 2
    sources = {click["source"] for click in clicks}
    assert sources == {"browser", "api"}

    summary = analytics.summary()
    assert summary["abc123"]["total_clicks"] == 2
    assert "last_click" in summary["abc123"]
    #assert summary["abc123"]["sources"] == {"browser", "api"}
    assert set(summary["abc123"]["sources"].keys()) == {"browser", "api"}

def test_log_click_invalid_slink(analytics):
    """
    Click logging for non-existent slink should still store valid flag.

    LLM Prompt Example:
        "Demonstrate logging clicks for slinks that might not exist yet."
    """
    analytics.log_click("nonexist", source="api", valid=False)
    clicks = analytics.get_clicks("nonexist")
    assert len(clicks) == 1
    assert clicks[0]["valid"] is False

def test_get_clicks_only_valid(analytics):
    """
    Test filtering clicks to only valid ones.

    LLM Prompt Example:
        "How would you test analytics for filtering clicks using the valid flag?"
    """
    analytics.log_click("abc", valid=True)
    analytics.log_click("abc", valid=False)
    valid_clicks = analytics.get_clicks("abc", only_valid=True)
    assert len(valid_clicks) == 1
    assert valid_clicks[0]["valid"] is True
