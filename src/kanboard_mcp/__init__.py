"""Multi-tenant MCP server for self-hosted Kanboard.

Each incoming request carries the caller's own Kanboard credential; the server
forwards it to Kanboard's JSON-RPC API so every action runs as that user, with
that user's permissions and authorship. The server itself is stateless and
stores no tokens.
"""

__version__ = "0.1.0"
