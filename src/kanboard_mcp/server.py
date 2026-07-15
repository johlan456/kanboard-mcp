"""FastMCP server entry point.

Serves the Kanboard tools over streamable HTTP so many clients (Claude Code,
Claude Desktop) can share one deployed instance. Each request authenticates as
its own user via headers — see :mod:`kanboard_mcp.auth`.
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from .config import get_settings
from .tools import register_tools

logger = logging.getLogger("kanboard_mcp")

INSTRUCTIONS = """\
Tools to read and manage a self-hosted Kanboard instance. Every call runs as the
authenticated user, so results and permissions are scoped to that person. Use
`whoami` to confirm identity, `list_my_projects`/`get_board` to orient, then the
task and comment tools. Column and swimlane ids for `move_task` come from
`get_board`.
"""


def build_server() -> FastMCP:
    """Construct the FastMCP server with all tools registered."""
    mcp = FastMCP(name="kanboard-mcp", instructions=INSTRUCTIONS)
    register_tools(mcp)
    return mcp


def main() -> None:
    """Console-script entry point: validate config, then serve over HTTP."""
    settings = get_settings()  # raises if KANBOARD_URL is unset — fail fast.
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info(
        "Starting kanboard-mcp on http://%s:%s/mcp (Kanboard: %s)",
        settings.host,
        settings.port,
        settings.kanboard_url,
    )
    mcp = build_server()
    mcp.run(transport="http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
