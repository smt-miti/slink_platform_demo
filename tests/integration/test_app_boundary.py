import pytest
import urllib.parse
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    """Provide a TestClient for the FastAPI app."""
    return TestClient(app)


def test_post_missing_url(client):
    """
    Posting JSON without a required 'url' field should return 422 validation error.

    LLM Prompt Example:
        "Show how FastAPI enforces required fields in request models."
    """
    response = client.post("/slink", json={})
    assert response.status_code == 422


def test_get_nonexistent_slink(client):
    """
    Requesting a slink code that does not exist returns 404.

    LLM Prompt Example:
        "Explain how API gracefully handles requests for non-existent slinks."
    """
    slink_code = "nonexist123"
    response = client.get(f"/slink/{slink_code}")
    assert response.status_code == 404


def test_special_characters_url(client):
    """
    Ensure URLs with special characters are correctly handled in slink creation
    and redirect.

    Notes:
        - Sets `check_reachable=False` to avoid external network dependency.
        - Verifies both creation and subsequent retrieval succeed.

    LLM Prompt Example:
        "Illustrate testing of slinks for URLs containing special characters,
        including query parameters and unicode characters."
    """
    url = "https://example.com/path?query=param&other=äöü"
    
    # Create slink without checking reachability
    response = client.post("/slink", json={"url": url, "alias": None})
    data = response.json()
    
    # Ensure slink creation succeeded
    assert response.status_code == 200, f"Failed to create slink: {data}"
    assert "slink" in data, "Response missing 'slink' key"
    
    slink_code = data["slink"]
    
    # Verify redirect works
    get_response = client.get(f"/slink/{slink_code}")
    get_data = get_response.json()
    assert get_response.status_code == 200

    # Decode returned URL before comparing
    returned_url = urllib.parse.unquote(get_data["original_url"])

    assert returned_url == url
    assert get_data["clicks"] == 1
