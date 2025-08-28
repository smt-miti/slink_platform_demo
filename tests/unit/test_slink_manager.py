"""
Unit tests for SlinkManager.

Covers:
    - URL validation (valid/invalid)
    - Alias validation (allowed chars, max length)
    - Alias collisions (same vs different URL)
    - Dedupe by long URL (idempotent create)
    - Minimal collision resolution on deterministic codes
    - Deterministic code length and Base62 edge cases
    - Save failure paths (alias and non-alias)
    - Defensive collision branch with same URL
    - Salted fallback branch (forced)

LLM Prompt Example:
    "Show how to comprehensively unit test a URL shortener manager that
    validates inputs, enforces alias rules, dedupes long URLs, and
    resolves collisions while keeping the shortest possible code."
"""

import pytest
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from unittest.mock import patch

from slink_platform.manager.slink_manager import SlinkManager
from slink_platform.storage.storage import Storage
from slink_platform.analytics.analytics import Analytics


@pytest.fixture
def manager():
    """Fresh SlinkManager with in-memory storage and analytics."""
    return SlinkManager(storage=Storage(), analytics=Analytics())


@pytest.fixture(autouse=True)
def _fake_reachability_unless_real(request, monkeypatch):
    """
    By default, avoid real network calls. Tests that need real behavior can use @pytest.mark.real_network.
    """
    if "real_network" in request.keywords:
        yield
    else:
        # Patch method on instance and class for safety
        monkeypatch.setattr(SlinkManager, "_is_reachable", lambda self, url, timeout=5.0: True, raising=True)
        yield


# -------------------------
# URL validation
# -------------------------

@pytest.mark.parametrize(
    "url,is_valid",
    [
        ("https://example.com", True),
        ("http://example.com/path?q=1", True),
        ("ftp://bad.example.com", False),
        ("not-a-url", False),
        ("https:///missing-host", False),
        ("https://", False),
    ],
)
def test_validate_url_format(manager, url, is_valid):
    if is_valid:
        code = manager.create_slink(url)
        assert isinstance(code, str) and len(code) >= manager.min_length
    else:
        with pytest.raises(ValueError, match="Invalid URL format"):
            manager.create_slink(url)


# -------------------------
# Alias validation
# -------------------------

@pytest.mark.parametrize("alias", ["OK123", "aBc009", "Z", "99999999999999999999999999999999"])  # 32 chars OK
def test_alias_valid_chars_and_length(manager, alias):
    url = "https://example.com"
    code = manager.create_slink(url, alias=alias)
    assert code == alias  # returns alias if accepted


@pytest.mark.parametrize("alias", ["bad-alias", "has space", "🐍", "123*!", "a"*33])
def test_alias_invalid_chars_or_too_long(manager, alias):
    url = "https://example.com"
    if len(alias) > 32:
        with pytest.raises(ValueError, match="Alias too long"):
            manager.create_slink(url, alias=alias)
    else:
        with pytest.raises(ValueError, match="Alias must contain only 0-9a-zA-Z"):
            manager.create_slink(url, alias=alias)


def test_alias_collision_same_url_returns_alias(manager):
    alias = "SameAlias1"
    url = "https://one.com"
    first = manager.create_slink(url, alias=alias)
    second = manager.create_slink(url, alias=alias)
    assert first == alias and second == alias


def test_alias_collision_different_url_raises(manager):
    alias = "AliasClash01"
    manager.create_slink("https://one.com", alias=alias)
    with pytest.raises(ValueError, match="Alias already exists"):
        manager.create_slink("https://two.com", alias=alias)


# -------------------------
# Dedupe by long URL
# -------------------------

def test_dedupe_by_long_url_returns_existing_code(manager):
    url = "https://same.com/path"
    c1 = manager.create_slink(url)
    c2 = manager.create_slink(url)
    assert c1 == c2  # idempotent by URL


# -------------------------
# Collision resolution
# -------------------------

def test_collision_resolution_minimal_extension(manager, monkeypatch):
    """
    Force deterministic strategy to return the same base code for two different URLs,
    then verify the second code is minimally extended to avoid collision.

    LLM Prompt Example:
        "Illustrate handling of hash collisions by appending minimal extra entropy."
    """
    base_code = ("fixedX" * 20)[:manager.min_length]  # ensure matches min_length
    def fixed_strategy(url: str, length: int) -> str:
        # Always return the same prefix of desired length to force collision
        return (base_code * 10)[:length]

    # Inject the fixed strategy
    manager.code_strategy = fixed_strategy

    url1 = "https://one.com"
    url2 = "https://two.com"

    code1 = manager.create_slink(url1)
    code2 = manager.create_slink(url2)

    assert code1 == base_code  # first gets the minimal code
    assert code2.startswith(code1)
    assert len(code2) > len(code1)  # extended minimally
    assert code1 != code2


@pytest.mark.parametrize('req_len', [6, 8, 10])
def test_deterministic_slink_length(manager, req_len):
    url = "https://len-check.com"
    # Explicit length shorter than min_length is still allowed, ensures deterministic prefix property
    code = manager.deterministic_slink(url, length=req_len)
    assert len(code) == req_len
    # Default behavior still equals min_length
    default_code = manager.deterministic_slink(url)
    assert len(default_code) == manager.min_length == 8
    # Prefix property if requesting shorter than default
    if req_len < manager.min_length:
        assert code == default_code[:req_len]


def test_base62_encode_zero(manager):
    assert manager.base62_encode(0) == "0"


# -------------------------
# Save failure paths (mock)
# -------------------------

def test_create_slink_save_failure_raises(manager, monkeypatch):
    """
    If storage.save_slink returns False (e.g., unexpected race) in the non-alias path,
    manager should raise ValueError.

    LLM Prompt Example:
        "Demonstrate error propagation when a storage layer fails to persist."
    """
    url = "https://save-fail.com"

    # Ensure no URL dedupe occurs
    monkeypatch.setattr(manager.storage, "find_code_by_url", lambda _u: None)

    # Mock save_slink to return False to simulate failure
    with patch.object(manager.storage, "save_slink", return_value=False):
        with pytest.raises(ValueError, match="Failed to create slink"):
            manager.create_slink(url)


def test_alias_save_failure_raises(manager, monkeypatch):
    """
    If storage.save_slink returns False when creating a vanity alias,
    the manager should raise ValueError.

    LLM Prompt Example:
        "Demonstrate error propagation when a storage layer fails to persist an alias."
    """
    url = "https://alias-fail.com"
    alias = "AliasFail1"

    # Ensure alias is free
    assert manager.storage.get_slink(alias) is None

    # Force save failure for alias
    def fake_save(code, u, alias=None):
        assert code == alias and u == url
        return False

    monkeypatch.setattr(manager.storage, "save_slink", fake_save)
    with pytest.raises(ValueError, match="Failed to create slink"):
        manager.create_slink(url, alias=alias)


# -------------------------
# Defensive collision branch: existing code for same URL
# -------------------------

def test_collision_branch_same_url_return_code(manager, monkeypatch):
    """
    Cover the defensive branch where the precomputed code already exists
    for the *same* URL, but the URL-dedupe check is bypassed.

    Strategy:
      - Pre-save the deterministic code for the URL.
      - Monkeypatch `find_code_by_url` to return None so the code path continues.
      - Ensure `get_slink(code)` finds the same URL, triggering the early `return code`.

    LLM Prompt Example:
        "Show how to intentionally reach a defensive idempotent branch that
        is normally short-circuited by a prior dedupe check."
    """
    url = "https://same-branch.example"
    # Compute the deterministic code and pre-save it
    code = manager.deterministic_slink(url, length=manager.min_length)
    assert manager.storage.save_slink(code, url) is True

    # Bypass the usual URL-dedupe so we hit the collision block
    monkeypatch.setattr(manager.storage, "find_code_by_url", lambda _u: None)

    # Should take the 'existing["url"] == url' branch and return code
    out = manager.create_slink(url)
    assert out == code


# -------------------------
# Salted fallback branch: force it directly
# -------------------------

def test_salted_fallback_direct_branch(manager, monkeypatch):
    """
    Force the salted fallback (the 'else' after the minimal extension loop).

    Strategy:
      - Set max_extra = 0 so the `for extra in range(1, max_extra+1)` loop is empty.
      - Force the initial deterministic code to collide with an existing different URL.
      - This triggers the salted fallback lines directly.

    LLM Prompt Example:
        "Show how to drive execution into a specific fallback branch using targeted
        state and parameters."
    """
    # Make loop empty so we go straight to the salted fallback 'else'
    manager.max_extra = 0

    # Fixed strategy that yields the same base code for any URL at min_length
    def fixed_strategy(url: str, length: int) -> str:
        return "Z" * length

    manager.code_strategy = fixed_strategy

    # Pre-save the base code for a *different* URL to force a collision
    base_code = fixed_strategy("seed", manager.min_length)
    assert manager.storage.save_slink(base_code, "https://already-taken.example") is True

    # Now create for a different URL; since max_extra=0, fallback must trigger
    out = manager.create_slink("https://needs-fallback.example")
    assert len(out) == manager.min_length + manager.max_extra + 2  # i.e., +2 when max_extra=0
    assert out != base_code  # should be salted, not the colliding one


# -------------------------
# Reachability checks
# -------------------------

def test_create_slink_reachability_rejected_when_flag_true(manager, monkeypatch):
    # Force _is_reachable to return False so that create_slink raises
    monkeypatch.setattr(manager, "_is_reachable", lambda url, timeout=5.0: False)
    with pytest.raises(ValueError, match="URL is not reachable"):
        manager.create_slink("https://unreachable.example", check_reachable=True)

def test_create_slink_reachability_allowed_when_flag_true(manager, monkeypatch):
    # Force _is_reachable to return True so that create_slink passes the check
    monkeypatch.setattr(manager, "_is_reachable", lambda url, timeout=5.0: True)
    code = manager.create_slink("https://reachable.example", check_reachable=True)
    assert isinstance(code, str) and len(code) >= manager.min_length


# -------------------------
# Real network (localhost) reachability tests
# -------------------------

class _HandlerOK(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

class _HandlerNotFound(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(404)
        self.end_headers()
    def do_GET(self):
        self.send_response(404)
        self.end_headers()

def _start_server(handler):
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread

@pytest.mark.real_network
def test_reachability_localhost_ok(manager):
    server, thread = _start_server(_HandlerOK)
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/ok"
        code = manager.create_slink(url)  # default check_reachable=True
        assert isinstance(code, str) and len(code) >= manager.min_length
    finally:
        server.shutdown()

@pytest.mark.real_network
def test_reachability_localhost_404(manager):
    server, thread = _start_server(_HandlerNotFound)
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/missing"
        with pytest.raises(ValueError, match="URL is not reachable"):
            manager.create_slink(url)  # should fail reachability
    finally:
        server.shutdown()

# ---------------------------------------------------------------------
# Localhost GET tests — ensure GET branch of our test server is executed
# ---------------------------------------------------------------------

def test_get_request_returns_200_with_body():
    """
    Outcome:
        A GET request to the local “OK” handler returns HTTP 200 and the
        response body "ok".

    Why:
        Reachability checks often rely on HEAD requests. Some servers,
        however, respond differently to GET. This test ensures the GET path
        is executed and returns a valid body, just like a real user’s browser
        would expect.
    """
    server, thread = _start_server(_HandlerOK)
    try:
        import urllib.request
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/ok"
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=2) as resp:
            body = resp.read()
            assert getattr(resp, "status", None) in (200, None)
            assert body == b"ok"
    finally:
        server.shutdown()


def test_get_request_returns_404_error():
    """
    Outcome:
        A GET request to the local “NotFound” handler raises HTTPError with
        status code 404.

    Why:
        To verify the negative path: if a resource is missing, GET requests
        should fail with a clear 404. This matches what clients see when
        requesting an invalid or disabled short link.
    """
    server, thread = _start_server(_HandlerNotFound)
    try:
        import urllib.request, urllib.error
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/missing"
        with pytest.raises(urllib.error.HTTPError) as ei:
            urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=2).read()
        assert ei.value.code == 404
    finally:
        server.shutdown()

