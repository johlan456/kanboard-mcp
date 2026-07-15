"""Regression tests for header retrieval from the live request context.

FastMCP's ``get_http_headers()`` strips the ``Authorization`` header by default,
which silently broke the Basic and Bearer credential schemes (the parser never
saw the header). These tests exercise the real seam: a Starlette ``Request`` is
placed into FastMCP's request contextvar — exactly what the HTTP transport does
— and we assert that :func:`kanboard_mcp.auth.request_headers` still exposes the
credential to :func:`kanboard_mcp.auth.parse_credentials`.
"""

from __future__ import annotations

import base64
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastmcp.server import dependencies
from starlette.requests import Request

from kanboard_mcp.auth import parse_credentials, request_headers


@contextmanager
def http_request(headers: dict[str, str]) -> Iterator[None]:
    """Simulate an in-flight HTTP request carrying ``headers``."""
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
        "root_path": "",
    }
    token = dependencies._current_http_request.set(Request(scope))
    try:
        yield
    finally:
        dependencies._current_http_request.reset(token)


def test_authorization_header_survives_retrieval():
    """The regression: Authorization must NOT be stripped from request headers."""
    with http_request({"Authorization": "Bearer alice:tok123"}):
        headers = request_headers()
    assert headers.get("authorization") == "Bearer alice:tok123"


def test_bearer_credentials_end_to_end():
    with http_request({"Authorization": "Bearer alice:tok123"}):
        assert parse_credentials(request_headers()) == ("alice", "tok123")


def test_basic_credentials_end_to_end():
    basic = "Basic " + base64.b64encode(b"bob:sekret").decode()
    with http_request({"Authorization": basic}):
        assert parse_credentials(request_headers()) == ("bob", "sekret")


def test_explicit_headers_end_to_end():
    with http_request({"X-Kanboard-Username": "carol", "X-Kanboard-Token": "t0k"}):
        assert parse_credentials(request_headers()) == ("carol", "t0k")


def test_no_request_context_yields_no_credentials():
    """Outside an HTTP request, header retrieval is empty and parsing fails."""
    from kanboard_mcp.auth import AuthError

    assert request_headers() == {}
    with pytest.raises(AuthError):
        parse_credentials(request_headers())
