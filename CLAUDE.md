# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync --extra dev          # install with dev deps
uv run pytest                # run all tests
uv run pytest tests/test_auth.py::test_bearer_user_token   # run a single test
uv run ruff check            # lint
uv run kanboard-mcp          # run the server (requires KANBOARD_URL, e.g. via .env)
```

Local smoke test without a real Kanboard: set `KANBOARD_URL` to a dead port
(`http://127.0.0.1:59999/jsonrpc.php`) — an authenticated tool call returning
"Connection refused" proves the credential made it through parsing and
forwarding. `GET /health` is an unauthenticated liveness probe.

## Architecture

Multi-tenant MCP server (FastMCP, streamable HTTP at `/mcp`) bridging MCP
clients to a self-hosted Kanboard JSON-RPC API. The core invariant: **the
server is stateless and holds no credentials** — every request carries the
caller's own Kanboard username + personal API token, and every Kanboard call
runs as that user so Kanboard enforces permissions and records authorship.

Request flow, spanning the three modules:

1. `tools.py` — each MCP tool calls `request_headers()` and passes the raw
   header dict to `auth.run(headers, "<kanboard_method>", **params)`.
2. `auth.py` — `parse_credentials()` extracts `(username, token)` from one of
   three schemes (`X-Kanboard-Username`/`X-Kanboard-Token`, HTTP Basic, or
   `Bearer user:token`), builds a short-lived `kanboard.Client`, and runs the
   blocking JSON-RPC call in a worker thread (`anyio.to_thread`).
3. `config.py` — env-only settings, resolved once (`lru_cache`). Deliberately
   contains no Kanboard credentials; only the shared `KANBOARD_URL`.

### Load-bearing details

- **`auth.request_headers()` exists because FastMCP's `get_http_headers()`
  strips the `Authorization` header by default**, which silently breaks the
  Basic/Bearer schemes. All header reads must go through `request_headers()`,
  never `get_http_headers()` directly. `tests/test_request_headers.py` guards
  this seam by injecting a Starlette Request into FastMCP's request contextvar
  (a private attribute — expect that test to break loudly on FastMCP major
  bumps).
- `fastmcp` is pinned `>=3.4,<4` for the same reason — re-verify header
  behavior before any major bump.
- The `kanboard` client resolves **any** snake_case method name via
  `__getattr__` → camelCase JSON-RPC (`get_me` → `getMe`), so adding a tool is
  just a new `@mcp.tool` wrapper in `tools.py` calling `auth.run()` with the
  Kanboard API method name — no client changes. Typos in method names fail at
  call time, not import time.
- All Kanboard failures (HTTP errors, bad auth, unreachable host) surface as
  `kanboard.ClientError` with a readable message; FastMCP forwards it as the
  tool error text.
- `parse_credentials()` is a pure function precisely so it stays unit-testable
  without a live request — keep it that way.

## Deployment context

Runs in Docker behind a Cloudflare Tunnel; TLS terminates at Cloudflare's
edge and the container port is published loopback-only. `/health` backs the
Docker `HEALTHCHECK`. Anyone who can reach the hostname can list tools —
per-user auth happens only at tool-call time, against Kanboard itself.
