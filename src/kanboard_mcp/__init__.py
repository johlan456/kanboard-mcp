"""Multi-tenant MCP server for self-hosted Kanboard.

Each incoming request carries the caller's own Kanboard credential; the server
forwards it to Kanboard's JSON-RPC API so every action runs as that user, with
that user's permissions and authorship. The server itself is stateless and
stores no tokens.
"""

from importlib.metadata import PackageNotFoundError, version

# Single source of truth is pyproject.toml; bump with `uv version --bump ...`.
try:
    __version__ = version("kanboard-mcp")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "0.0.0+unknown"
