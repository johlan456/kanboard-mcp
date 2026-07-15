"""Per-request authentication — the heart of the multi-tenant design.

Every tool call runs as the *calling employee*, never as a shared identity. The
caller's Kanboard credential arrives on each HTTP request; we parse it, build a
short-lived :class:`kanboard.Client` bound to that credential, and let Kanboard
enforce that user's permissions. Nothing is persisted and the token is never
logged.

Accepted credential schemes (checked in this order):

1. Explicit headers::

       X-Kanboard-Username: <kanboard username>
       X-Kanboard-Token:    <that user's personal API token>

2. HTTP Basic::

       Authorization: Basic base64("<username>:<token>")

3. Bearer carrying "username:token"::

       Authorization: Bearer <username>:<token>

For per-user identity use the employee's **personal** API token (Kanboard →
profile → API) with their real username. The app-wide ``jsonrpc`` token also
works but is admin-level and bypasses per-user permissions — avoid it here.
"""

from __future__ import annotations

import base64
import binascii

import anyio
import kanboard

from .config import get_settings


class AuthError(Exception):
    """Raised when a request carries no usable Kanboard credential."""


def parse_credentials(headers: dict[str, str]) -> tuple[str, str]:
    """Extract ``(username, token)`` from request headers.

    ``headers`` keys are treated case-insensitively. Pure function — no I/O — so
    it is unit-testable without a live request.

    Raises:
        AuthError: if no recognised, well-formed credential is present.
    """
    h = {k.lower(): v for k, v in headers.items()}

    # 1. Explicit X-Kanboard-* headers.
    username = (h.get("x-kanboard-username") or "").strip()
    token = (h.get("x-kanboard-token") or "").strip()
    if username and token:
        return username, token

    # 2 & 3. Authorization header.
    authz = (h.get("authorization") or "").strip()
    if authz:
        scheme, _, value = authz.partition(" ")
        scheme = scheme.lower()
        value = value.strip()

        if scheme == "basic":
            try:
                decoded = base64.b64decode(value, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError) as exc:
                raise AuthError("Malformed HTTP Basic Authorization header.") from exc
            user, sep, tok = decoded.partition(":")
            if sep and user and tok:
                return user, tok
            raise AuthError('HTTP Basic credential must be "username:token".')

        if scheme == "bearer":
            user, sep, tok = value.partition(":")
            if sep and user and tok:
                return user, tok
            raise AuthError('Bearer credential must be "username:token".')

    raise AuthError(
        "No Kanboard credential found. Provide X-Kanboard-Username + X-Kanboard-Token, "
        "or an Authorization header (Basic base64(user:token), or Bearer user:token)."
    )


def client_from_headers(headers: dict[str, str]) -> kanboard.Client:
    """Build a per-request :class:`kanboard.Client` from request headers."""
    username, token = parse_credentials(headers)
    settings = get_settings()
    return kanboard.Client(
        url=settings.kanboard_url,
        username=username,
        password=token,
        timeout=settings.request_timeout,
        user_agent="kanboard-mcp",
    )


async def run(headers: dict[str, str], method: str, /, **params):
    """Call a Kanboard API ``method`` as the caller, off the event loop.

    Reads the credential from ``headers`` (already captured in the request
    context by the caller), then runs the blocking JSON-RPC request in a worker
    thread so the async server stays responsive.

    Example:
        ``await run(headers, "create_task", project_id=1, title="Hi")``
    """
    client = client_from_headers(headers)

    def _call():
        with client:
            return getattr(client, method)(**params)

    return await anyio.to_thread.run_sync(_call)
