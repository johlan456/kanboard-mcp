"""Unit tests for credential parsing — the security-critical seam."""

from __future__ import annotations

import base64

import pytest

from kanboard_mcp.auth import AuthError, parse_credentials


def _basic(user: str, token: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{token}".encode()).decode()


def test_explicit_headers():
    creds = parse_credentials({"X-Kanboard-Username": "alice", "X-Kanboard-Token": "tok123"})
    assert creds == ("alice", "tok123")


def test_explicit_headers_case_insensitive():
    creds = parse_credentials({"x-kanboard-username": "bob", "X-KANBOARD-TOKEN": "tok"})
    assert creds == ("bob", "tok")


def test_basic_auth():
    creds = parse_credentials({"Authorization": _basic("carol", "sekret")})
    assert creds == ("carol", "sekret")


def test_bearer_user_token():
    creds = parse_credentials({"Authorization": "Bearer dave:mytoken"})
    assert creds == ("dave", "mytoken")


def test_explicit_headers_take_precedence_over_authorization():
    creds = parse_credentials(
        {"X-Kanboard-Username": "alice", "X-Kanboard-Token": "t", "Authorization": "Bearer x:y"}
    )
    assert creds == ("alice", "t")


def test_missing_credentials_raises():
    with pytest.raises(AuthError):
        parse_credentials({})


def test_partial_explicit_headers_raise():
    with pytest.raises(AuthError):
        parse_credentials({"X-Kanboard-Username": "alice"})


def test_malformed_basic_raises():
    with pytest.raises(AuthError):
        parse_credentials({"Authorization": "Basic not-base64!!"})


def test_basic_without_colon_raises():
    bad = "Basic " + base64.b64encode(b"nocolon").decode()
    with pytest.raises(AuthError):
        parse_credentials({"Authorization": bad})


def test_bearer_without_colon_raises():
    with pytest.raises(AuthError):
        parse_credentials({"Authorization": "Bearer justatoken"})
