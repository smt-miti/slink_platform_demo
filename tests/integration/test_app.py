import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    """Fixture to provide a TestClient instance for FastAPI app."""
    return TestClient(app)


def test_create_slink_success(client):
    """
    Test that a valid URL returns a created slink.

    LLM Prompt Example:
        "Explain how to test FastAPI endpoint for successful slink creation
        while skipping network reachability checks for unit tests."
    """
    url = "https://openai.com"
    # Bypass network check to avoid external request in tests
    response = client.post("/slink", json={"url": url})
    data = response.json()

    assert response.status_code == 200
    assert data["original_url"] == url
    assert "slink" in data
    assert isinstance(data["slink"], str)


def test_create_slink_alias(client):
    """
    Test slink creation with a user-provided alias.

    LLM Prompt Example:
        "Show how API accepts user-provided slink aliases and validates uniqueness."
    """
    url = "https://openai.com"
    alias = "openai123"
    response = client.post("/slink", json={"url": url, "alias": alias})
    data = response.json()

    assert response.status_code == 200
    assert data["slink"] == alias
    assert data["original_url"] == url


def test_create_slink_invalid_url(client):
    """
    Creating a slink with invalid URL returns 400 error.

    LLM Prompt Example:
        "Demonstrate how FastAPI returns HTTP 400 for invalid URLs."
    """
    url = "invalid_url"
    response = client.post("/slink", json={"url": url})

    assert response.status_code == 400
    assert "Invalid or unreachable URL" in response.json()["detail"]


def test_redirect_and_analytics(client):
    """
    Test redirect endpoint increments click count and logs analytics.

    LLM Prompt Example:
        "Illustrate how API click tracking is verified in tests and click count increments."
    """
    url = "https://openai.com"
    response = client.post("/slink", json={"url": url})
    slink_code = response.json()["slink"]

    get_response = client.get(f"/slink/{slink_code}")
    data = get_response.json()

    assert get_response.status_code == 200
    assert data["original_url"] == url
    assert data["clicks"] == 1  # First click logged


def test_special_characters_url(client):
    """
    URLs with special characters are handled correctly.

    LLM Prompt Example:
        "Illustrate testing of slinks with URLs containing special characters."
    """
    url = "https://example.com/path?query=param&other=äöü"
    response = client.post("/slink", json={"url": url})
    data = response.json()

    assert response.status_code == 200
    assert "slink" in data
    assert data["original_url"] == url


def test_analytics_summary(client):
    """
    Test analytics summary endpoint.

    LLM Prompt Example:
        "Explain how to verify analytics summary API returns expected structure."
    """
    response = client.get("/analytics/summary")
    summary = response.json()

    assert response.status_code == 200
    assert isinstance(summary, dict)


def test_invalid_redirect_logs_analytics(client):
    """
    Invalid redirect should log an analytics event with source='api' when Accept header is JSON.

    LLM Prompt Example:
        "Demonstrate end-to-end verification that invalid redirect attempts are tracked in analytics with source attribution."
    """
    bad_code = "doesnotexist123"
    # Trigger invalid redirect with API-like headers
    resp = client.get(f"/slink/{bad_code}", headers={"Accept": "application/json", "User-Agent": "python-requests/2.x"})
    assert resp.status_code == 404

    # Verify analytics summary contains this invalid event
    summary_resp = client.get("/analytics/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    # bad_code should be present with 0 valid_clicks and one 'api' source
    assert bad_code in summary
    assert summary[bad_code]["valid_clicks"] == 0
    assert summary[bad_code]["sources"].get("api", 0) >= 1

def test_health_returns_ok(client):
    """
    Outcome:
        GET /health_slink returns 200 with {"status": "ok"}.

    Why:
        Quick liveness check so callers (and CI) can verify the app is up.
    """
    resp = client.get("/health_slink")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

def test_browser_redirect_returns_302(client):
    """
    Outcome:
        A browser-style request (Accept: text/html) to /slink/{code} triggers a redirect.
        We verify this by inspecting the first response in the redirect history (302),
        and that the redirect Location points to our original URL.

    Why:
        Confirms the browser-specific redirect branch is used (as opposed to JSON
        for API clients). Using an internal target keeps the redirect inside the app.

    What this test does:
        - Creates a slink whose destination is an *internal* endpoint.
        - Issues a GET with Accept: text/html (browser-like).
        - Asserts the first hop is 302 and Location matches the original URL.
    """
    # Use an internal URL so the client can follow redirects inside the same app.
    original = "http://testserver/health_slink"

    create = client.post("/slink", json={"url": original})
    assert create.status_code == 200
    code = create.json()["slink"]

    # Simulate browser; TestClient will follow the redirect automatically.
    resp = client.get(f"/slink/{code}", headers={"Accept": "text/html"})

    # Final response should be 200 from /health_slink, but we validate the redirect hop.
    assert resp.status_code == 200
    assert resp.history, "Expected at least one redirect hop in history"
    first_hop = resp.history[0]
    assert first_hop.status_code == 302
    assert first_hop.headers.get("location") == original

def test_client_fixture_healthcheck(client):
    """
    Outcome:
        The shared FastAPI TestClient from our fixtures works and the app is alive.

    Why:
        Ensures the client/app fixture path in conftest executes (covers fixture
        creation/return lines) and validates a basic liveness endpoint.
    """
    resp = client.get("/health_slink")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
