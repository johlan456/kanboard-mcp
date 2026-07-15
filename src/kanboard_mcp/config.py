"""Server configuration — read once at startup from the environment.

Deliberately holds NO Kanboard credentials. Credentials are per-user and arrive
on each request (see :mod:`kanboard_mcp.auth`). The only Kanboard-related value
here is the URL of the JSON-RPC endpoint, which is the same for everyone.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    """Process-wide settings resolved from environment variables."""

    kanboard_url: str
    """Kanboard JSON-RPC endpoint, e.g. ``https://kanboard.example.com/jsonrpc.php``."""

    host: str
    port: int
    log_level: str
    request_timeout: int
    """Per-request timeout (seconds) for calls to Kanboard."""


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Build :class:`Settings` from ``env`` (defaults to ``os.environ``).

    Raises:
        ValueError: if ``KANBOARD_URL`` is missing. Everything else has a default.
    """
    e = os.environ if env is None else env

    url = (e.get("KANBOARD_URL") or "").strip()
    if not url:
        raise ValueError(
            "KANBOARD_URL is required — set it to your Kanboard JSON-RPC endpoint, "
            "e.g. https://kanboard.example.com/jsonrpc.php"
        )

    return Settings(
        kanboard_url=url,
        host=e.get("HOST", "127.0.0.1"),
        port=int(e.get("PORT", "8000")),
        log_level=e.get("LOG_LEVEL", "INFO").upper(),
        request_timeout=int(e.get("KANBOARD_TIMEOUT", "30")),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide settings, resolved once from ``os.environ``."""
    return load_settings()
