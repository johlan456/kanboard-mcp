"""Tool-level behavior tests."""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from kanboard_mcp import tools

FULL_GETME_ROW = {
    "id": 19,
    "username": "johlan",
    "name": "Johlan Pretorius",
    "email": "johlan@example.com",
    "role": "app-admin",
    "timezone": "Africa/Johannesburg",
    # Fields that must never be forwarded to the client:
    "api_access_token": "SECRET-TOKEN",
    "twofactor_secret": "SECRET-2FA",
    "google_id": "1234567890",
    "nb_failed_login": 0,
}


@pytest.mark.anyio
async def test_whoami_strips_sensitive_fields(monkeypatch):
    async def fake_run(headers, method, **params):
        assert method == "get_me"
        return dict(FULL_GETME_ROW)

    monkeypatch.setattr(tools, "run", fake_run)
    monkeypatch.setattr(tools, "request_headers", lambda: {})

    mcp = FastMCP("test")
    tools.register_tools(mcp)
    whoami = await mcp.get_tool("whoami")
    result = await whoami.fn()

    assert result == {
        "id": 19,
        "username": "johlan",
        "name": "Johlan Pretorius",
        "email": "johlan@example.com",
        "role": "app-admin",
        "timezone": "Africa/Johannesburg",
    }
    assert "api_access_token" not in result
    assert "twofactor_secret" not in result


@pytest.fixture
def anyio_backend():
    return "asyncio"
