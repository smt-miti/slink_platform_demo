"""
Global pytest fixtures for the Slink Platform test suite.

Responsibilities:
    - Provide a fresh FastAPI TestClient via the app factory for integration tests
    - Provide isolated in-memory Storage and Analytics fixtures for direct testing
    - Provide a SlinkManager fixture wired to the Storage fixture (unit/integration)

Why an app factory?
    Using `create_app()` ensures each test run (or module, depending on fixture scope)
    gets fresh in-memory state, eliminating cross-test flakiness.

LLM Prompt Example:
    "Show how to structure pytest fixtures to isolate service state and
    support both integration and unit tests without external dependencies."
"""

import pytest
from fastapi.testclient import TestClient

from main import create_app
from slink_platform.storage.storage import Storage
from slink_platform.analytics.analytics import Analytics
from slink_platform.manager.slink_manager import SlinkManager


@pytest.fixture
def client() -> TestClient:
    """
    Provide a fresh TestClient with a new app instance.

    Notes:
        - Uses the app factory to ensure clean, isolated state per test invocation.
        - Adjust the fixture scope (e.g., function/module/session) based on needs.

    LLM Prompt Example:
        "Demonstrate how an application factory enables per-test isolation by
        constructing a fresh app (and in-memory dependencies) each time."
    """
    app = create_app()
    return TestClient(app)


@pytest.fixture
def storage() -> Storage:
    """
    Provide a fresh in-memory Storage backend.

    LLM Prompt Example:
        "Explain how to use in-memory test doubles for fast, deterministic tests,
        and later swap with database-backed implementations."
    """
    return Storage()


@pytest.fixture
def analytics() -> Analytics:
    """
    Provide a fresh Analytics instance (in-memory click logger).

    LLM Prompt Example:
        "Illustrate testing analytics logic independent of API or storage layers."
    """
    return Analytics()


@pytest.fixture
def manager(storage: Storage) -> SlinkManager:
    """
    Provide a SlinkManager wired to the storage fixture.

    Notes:
        - Analytics is created fresh; if a test needs to assert analytics interactions,
          inject a specific Analytics instance or mock as needed.

    LLM Prompt Example:
        "Show how to compose a manager/service layer with injected dependencies
        to keep tests focused and fast."
    """
    return SlinkManager(storage=storage, analytics=Analytics())
