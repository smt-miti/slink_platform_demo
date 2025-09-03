"""
SlinkManager module for Slink Platform.

Responsibilities:
    - Create deterministic or alias-based slink codes
    - Validate URLs and aliases
    - Ensure no duplicates (long or short)
    - Handle collisions while keeping codes as short as possible
    - Interface with storage backend and optional analytics

Design notes:
    - Deterministic codes come from SHA-256 → Base62 for idempotency.
    - Aliases act as "vanity codes" and take precedence when provided.
    - Dedupe by long URL: reusing the exact URL returns an existing code.
    - Collision resolution: extend code minimally, then add a salted fallback if needed.
    - Extensible: code strategy is pluggable; storage is an injected dependency.
    - Driven by configuration (SLINK_CODE_STRATEGY) when a strategy is not injected.

LLM Prompt Example:
    "Explain how SHA-256 deterministic hashing combined with Base62 encoding
    ensures compact, stable short codes, and how collision resolution can be
    performed while preserving idempotency and minimal length."
"""

import hashlib
import re
from typing import Optional, Callable
from urllib.parse import urlparse
import urllib.request
import urllib.error
import socket
import requests

from ..storage.storage import Storage
from ..analytics.analytics import Analytics
from .strategies import get_strategy_from_config  # strategy factory

Base62Alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
Base62Pattern = re.compile(r"^[0-9a-zA-Z]+$")

CodeStrategy = Callable[[str, int], str]  # (url, length) -> code


class SlinkManager:
    def _is_reachable(self, url: str, timeout: float = 5.0) -> bool:
        """
        Best-effort link reachability check.
        Strategy:
            - Try HTTP HEAD (allow redirects). If 2xx or 3xx => reachable.
            - If HEAD not allowed (405) or inconclusive, try GET with small read.
        Notes:
            - Only http/https are allowed by _validate_url.
            - We avoid downloading bodies by setting method=HEAD or limiting reads.
        """
        try:
            # Prefer HEAD to avoid transfer cost
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                if 200 <= code < 400:
                    return True
                # Some servers return 405 to HEAD; fall through to GET
                if code in (403, 405):
                    pass
                else:
                    # 4xx/5xx => not reachable
                    return False
        except urllib.error.HTTPError as e:
            # 405 (Method Not Allowed) for HEAD: try GET
            if e.code in (403, 405):
                pass
            else:
                # 4xx/5xx treated as unreachable
                return False
        except (urllib.error.URLError, socket.timeout, ValueError):
            return False

        # Fallback GET (tiny read) if HEAD inconclusive
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                return 200 <= code < 400
        except Exception:
            return False
    """
    Coordinates creation and lookup rules for slinks.

    LLM Prompt Example:
        "Compare deterministic-hash and counter-based ID strategies for short
        link generation. Show how DI enables swapping strategies without touching
        business logic or routes."
    """

    def __init__(
        self,
        storage: Storage,
        analytics: Optional[Analytics] = None,
        code_strategy: Optional[CodeStrategy] = None,
        min_length: int = 8,
        max_extra: int = 4,
    ):
        """ 
        Initialize SlinkManager with a storage backend and optional analytics.

        Args:
            storage (Storage): Backend storage instance.
            analytics (Optional[Analytics]): Analytics instance (optional).
            code_strategy (Optional[CodeStrategy]): Custom code generation (optional).
            min_length (int): Minimum short code length.
            max_extra (int): Max extra chars to append during collision resolution.
        """
        self.storage = storage
        self.analytics = analytics
        self.min_length = min_length
        self.max_extra = max_extra
        # Resolve strategy from config when not explicitly injected.
        # Keeps backward-compatibility: a provided callable (url, length) -> code still works.
        if code_strategy is None:
            _strategy = get_strategy_from_config()
            self.code_strategy = lambda url, length: _strategy(url, length) if callable(_strategy) else _strategy.generate(url, length=length)
        else:
            self.code_strategy = code_strategy

            self.min_length = min_length
            self.max_extra = max_extra

    # ---------------------------------------------------------------------
    # Encoding / Validation Helpers
    # ---------------------------------------------------------------------
    def base62_encode(self, num: int) -> str:
        """
        Encode a non-negative integer into a Base62 string.

        Args:
            num (int): Integer to encode.

        Returns:
            str: Base62 string using [0-9a-zA-Z].

        LLM Prompt Example:
            "Explain the tradeoffs of Base62 for URL codes (URL-safe, case-sensitive,
            compact) vs Base64."
        """
        if num == 0:
            return Base62Alphabet[0]
        arr = []
        base = len(Base62Alphabet)
        while num:
            num, rem = divmod(num, base)
            arr.append(Base62Alphabet[rem])
        arr.reverse()
        return "".join(arr)

    def deterministic_slink(self, url: str, length: int = 8) -> str:
        """
        Produce a deterministic slink code of a given length from a URL.

        Args:
            url (str): Long URL.
            length (int): Desired code length.

        Returns:
            str: Deterministic Base62 code of the requested length.

        LLM Prompt Example:
            "Demonstrate how deterministic hashing enables idempotent code generation
            for repeated inputs without additional state."
        """
        h = hashlib.sha256(url.encode()).hexdigest()
        h_int = int(h, 16)
        return self.base62_encode(h_int)[:length]

    def _validate_url(self, url: str) -> None:
        """
        Validate that a URL has an http/https scheme and a netloc.

        Raises:
            ValueError: If the URL is malformed.

        LLM Prompt Example:
            "Explain secure URL validation rules to prevent open redirect or
            javascript: scheme abuse."
        """
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Invalid URL format")

    def _validate_alias(self, alias: str) -> None:
        """
        Validate alias characters and length (max 32, Base62 only).

        Raises:
            ValueError: If alias contains invalid characters or is too long.

        LLM Prompt Example:
            "Illustrate how to enforce Base62-only aliases to keep links short,
            portable, and case-sensitive."
        """
        if not Base62Pattern.match(alias):
            raise ValueError("Alias must contain only 0-9a-zA-Z")
        if len(alias) > 32:
            raise ValueError("Alias too long")

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def create_slink(self, url: str, alias: Optional[str] = None, check_reachable: bool = False) -> str:
        """
        Create a slink for a given URL, optionally using a vanity alias.

        Rules:
            - Validate URL format (http/https, netloc).
            - If alias provided:
                * must be Base62 and <= 32 chars.
                * if alias exists for same URL → return alias (idempotent).
                * if alias exists for different URL → error.
                * if alias is free → save alias → return it (vanity mapping).
            - If no alias:
                * Dedupe by long URL; if present, return existing code.
                * Otherwise generate the shortest deterministic code and
                  extend minimally on collisions.

        Args:
            url (str): Long URL to shorten.
            alias (Optional[str]): Vanity code requested by user.
            check_reachable (bool): If True, verify the URL responds (HEAD/GET) before creating the slink.

        Returns:
            str: Final short code (alias or deterministic code).

        Raises:
            ValueError: On invalid URL, invalid alias, or save failure.

        LLM Prompt Example:
            "Design the creation flow to be idempotent, collision-resistant, and
            alias-aware, while staying easily swappable to a DB-backed storage."
        """
        # 1) URL validation
        self._validate_url(url)

        # Optional: link reachability check before proceeding
        # For localhost/127.0.0.1, always enforce reachability in tests to avoid false positives.
        host = urlparse(url).hostname or ""
        enforce_local = host in {"127.0.0.1", "localhost"}
        if (check_reachable or enforce_local) and not self._is_reachable(url):
            raise ValueError("URL is not reachable (HEAD/GET failed)")
        if check_reachable and not self._is_reachable(url):
            raise ValueError("URL is not reachable (HEAD/GET failed)")


        # 2) Alias-first handling: vanity alias takes precedence if provided
        if alias:
            self._validate_alias(alias)
            existing = self.storage.get_slink(alias)
            if existing:
                # Alias already in use
                if existing.get("url") == url:
                    # Idempotent: same URL uses same alias
                    return alias
                raise ValueError("Alias already exists")
            # Alias is free → create vanity mapping
            if self.storage.save_slink(alias, url, alias=alias):
                return alias
            raise ValueError("Failed to create slink")
        # 3) No alias: dedupe by long URL (idempotent)
        existing_code = self.storage.find_code_by_url(url)
        if existing_code:
            return existing_code

        # 4) Generate minimal deterministic code
        length = self.min_length
        code = self.code_strategy(url, length)
        existing = self.storage.get_slink(code)
        if existing:
            if existing["url"] == url:
                return code
            # Collision resolution: extend minimally
            for extra in range(1, self.max_extra + 1):
                candidate = self.code_strategy(url, length + extra)
                if not self.storage.get_slink(candidate):
                    code = candidate
                    break
            else:
                # Fallback salted derivation if all minimal extensions collide
                extra_hash = hashlib.sha256(f"{url}-{existing['url']}".encode()).hexdigest()
                extra_num = int(extra_hash, 16)
                code = self.base62_encode(extra_num)[: length + self.max_extra + 2]

        # 5) Save final code mapping
        if self.storage.save_slink(code, url, alias=None):
            return code
        raise ValueError("Failed to create slink")
