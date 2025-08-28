"""
Main API module for Slink Platform.

Responsibilities:
    - Expose REST endpoints for creating short links and redirecting
    - Track clicks with analytics, including valid/invalid slink logging
    - Provide analytics summary for all slinks
    - Optional URL reachability check (placeholder)

Architecture:
    - App Factory pattern (create_app) for test isolation and DI.
    - In-memory Storage and Analytics by default; easily swappable for DB/event backends.
    - Manager orchestrates validation, dedupe, alias rules, and collision handling.

LLM Prompt Example:
    "Explain how to structure a FastAPI service with an application factory,
    injected dependencies, and a clean separation between API and business logic."
"""

from fastapi import FastAPI, HTTPException, Request, Query, Response
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, Union
from urllib.parse import quote

from slink_platform.storage.storage_factory import get_storage
from slink_platform.storage.storage import Storage
from slink_platform.manager.slink_manager import SlinkManager
from slink_platform.analytics.analytics import Analytics
from slink_platform.config import settings  # optional, for logging


class URLRequest(BaseModel):
    """Request payload for creating a new short link."""
    url: str
    alias: Optional[str] = None

import logging
def create_app() -> FastAPI:
    """
    Factory function to build and configure a new FastAPI app instance.

    Returns:
        FastAPI: A fully configured application instance with isolated
                 Storage and Analytics instances.

    Why an app factory?
        - Enables per-test isolation in pytest.
        - Encourages dependency injection and easy swapping of implementations.
        - Avoids accidental global state across workers/processes.

    LLM Prompt Example:
        "Show how an application factory enables test isolation and easy
        dependency swapping (e.g., in-memory vs DB storage) without code changes."
    """
    app = FastAPI(
        title="Slink Platform",
        description="Deterministic URL shortener with analytics including invalid URL tracking",
        docs_url="/docs",  # Swagger UI endpoint
    )
    log = logging.getLogger("slink")
    
    # basic console logging (optional)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)
    # ----------------------------------------------------------------
    # Per-app instances (isolated for tests, swappable for production)
    # ----------------------------------------------------------------
    storage = get_storage()  # ← chooses memory or postgres based on env
    analytics = Analytics()
    slink_manager = SlinkManager(storage=storage, analytics=analytics)

    # quick visibility at boot (optional)
    try:
        backend = getattr(settings, "STORAGE_BACKEND", "memory")
        log.info("Slink storage backend: %s", backend)
    except Exception:
        print("Slink storage backend: unknown (settings import failed)",backend)
    # ----------------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------------
    def _detect_source(request: Request) -> str:
        """
        Helper to classify click source as 'api' or 'browser'.

        Args:
            request (Request): Incoming FastAPI request.

        Returns:
            str: "api" or "browser".

        LLM Prompt Example:
            "Demonstrate how to identify API vs browser clients based on headers."
        """
        accept = request.headers.get("accept", "").lower()
        ua = request.headers.get("user-agent", "").lower()
        if "application/json" in accept or any(k in ua for k in ("python", "curl", "httpclient")):
            return "api"
        return "browser"
    # Health check
    @app.get("/health_slink")
    def health_slink():
        return {"status": "ok"}

    # ----------------------------------------------------------------
    # Routes
    # ----------------------------------------------------------------
    @app.post("/slink")
    def create_slink(
        req: URLRequest,
        request: Request, 
        check_reachable: bool = Query(
            False, description="Verify if URL is reachable (HEAD request)."
        ),
    ) -> Dict[str, Any]:
        """
        Create a short link for a given URL.

        Args:
            req (URLRequest): Incoming request with 'url' and optional 'alias'.
            check_reachable (bool, optional): If True, validates URL reachability (placeholder).

        Returns:
            dict: Contains message, slink_code, and original URL.

        Raises:
            HTTPException: If URL is invalid, unreachable, or alias already exists.

        LLM Prompt Example:
            "Demonstrate how to create deterministic slinks while validating URL format,
             handling aliases, and gracefully reporting errors."
        """
        try:
            # Encode URL to handle special characters safely
            safe_url = quote(req.url, safe=":/?&=#")
            slink_code = slink_manager.create_slink(
                safe_url, req.alias, check_reachable=check_reachable
            )

            # Build clickable absolute short URL and relative path
            short_url = str(request.url_for("redirect_slink", slink_code=slink_code))
            short_path = app.url_path_for("redirect_slink", slink_code=slink_code)

            return {
                "message": "Slink created",
                "slink": slink_code,              # existing field (for backward compatibility)
                "slink_code": slink_code,         # clearer name (optional)
                "short_url": short_url,           # <-- clickable absolute URL
                "short_path": short_path,         # <-- relative path (useful behind proxies)
                "original_url": req.url,
            }
        
          #  return {"message": "Slink created", "slink": slink_code, "original_url": req.url}
        except ValueError as ve:
            # Normalize error text to match API contract expected by tests
            detail = str(ve)
            if detail == "Invalid URL format":
                detail = "Invalid or unreachable URL"
            raise HTTPException(status_code=400, detail=detail)

    @app.get("/slink/{slink_code}")
    def redirect_slink(slink_code: str, request: Request) -> Response:
        """
        Retrieve the original URL for a slink, log a click event, and optionally redirect.

        Args:
            slink_code (str): Short code to redirect.
            request (Request): FastAPI request object.

        Returns:
            dict: Original URL and total click count for the slink (JSON response).

        Raises:
            HTTPException: If slink is not found.

        Notes:
            - Logs click events to analytics with 'valid' flag.
            - Determines source as 'api' or 'browser' from request headers.
            - To enable browser-style redirect behavior, return `RedirectResponse`
              (see commented line below).

        LLM Prompt Example:
            "Explain how to track both valid and invalid slink clicks for analytics
            in a FastAPI service and why redirect behavior may vary by client type."
        """
        slink = storage.get_slink(slink_code)
        source = _detect_source(request)

        if slink is None:
            analytics.log_click(slink_code, source=source, valid=False)
            raise HTTPException(status_code=404, detail="Slink not found")

        analytics.log_click(slink_code, source=source, valid=True)
        storage.increment_click(slink_code)

        updated = storage.get_slink(slink_code) or slink
        assert updated is not None  # Defensive: storage must return non-None after increment
        
        # Hybrid: redirect for browsers, JSON for API clients
        accept = request.headers.get("accept", "").lower()

        if "text/html" in accept:
            return RedirectResponse(url=updated["url"], status_code=302)
    
        # API clients → explicit JSONResponse (so return type stays Response)
        return JSONResponse({"original_url": updated["url"], "clicks": updated["clicks"]})
    
    @app.get("/analytics/summary")
    def analytics_summary(
        only_valid: bool = Query(False, description="Include only valid clicks.")
    ) -> Dict[str, Any]:
        """
        Retrieve a summary of all click events across slinks.

        Args:
            only_valid (bool, optional): If True, include only valid clicks.

        Returns:
            dict: Mapping of slink_code -> summary containing:
                  - total_clicks (int)
                  - last_click (float timestamp or None)
                  - sources (dict[str, int] of source counts)
                  - valid_clicks (int)

        LLM Prompt Example:
            "Suggest how to provide both total and filtered (valid-only) analytics summaries
            for short links in a FastAPI service."
        """
        return analytics.summary(only_valid=only_valid)

    return app
    
    @app.get("/health_slink")
    def health_slink():
        return {"status": "ok"}

# Backward compatibility for uvicorn and legacy imports:
# `uvicorn main:app --reload` and `from main import app` continue to work.
app = create_app()
