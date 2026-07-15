"""Kanboard tool surface exposed over MCP.

Every tool runs as the calling employee: it reads the per-request credential
from the incoming HTTP headers and forwards the JSON-RPC call under that
identity. Kanboard then applies that user's permissions and records authorship.

This is a deliberately small starter set (~11 tools). Because the underlying
``kanboard`` client exposes *every* API method by dynamic dispatch, adding more
is a few lines each — expand as the team needs.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from .auth import request_headers, run


def _clean(**kwargs: Any) -> dict[str, Any]:
    """Drop ``None`` values so we only send parameters the caller actually set."""
    return {k: v for k, v in kwargs.items() if v is not None}


def register_tools(mcp: FastMCP) -> None:
    """Register all Kanboard tools on ``mcp``."""

    # ---- Identity ---------------------------------------------------------

    @mcp.tool
    async def whoami() -> dict:
        """Return the authenticated Kanboard user (id, username, name, role).

        Useful to confirm the connector is authenticated as the right person.
        """
        # getMe returns the full user row, including api_access_token and 2FA
        # secrets — never forward it verbatim.
        me = await run(request_headers(), "get_me")
        return {
            key: me.get(key)
            for key in ("id", "username", "name", "email", "role", "timezone")
        }

    # ---- Projects ---------------------------------------------------------

    @mcp.tool
    async def list_my_projects() -> Any:
        """List the projects the authenticated user is a member of."""
        return await run(request_headers(), "get_my_projects")

    @mcp.tool
    async def get_project(project_id: int) -> Any:
        """Get a single project's details by id."""
        return await run(request_headers(), "get_project_by_id", project_id=project_id)

    @mcp.tool
    async def get_board(project_id: int) -> Any:
        """Get a project's full board: swimlanes, columns, and the tasks in each."""
        return await run(request_headers(), "get_board", project_id=project_id)

    # ---- Tasks (read) -----------------------------------------------------

    @mcp.tool
    async def get_task(task_id: int) -> Any:
        """Get a single task by id."""
        return await run(request_headers(), "get_task", task_id=task_id)

    @mcp.tool
    async def search_tasks(project_id: int, query: str) -> Any:
        """Search tasks in a project using Kanboard's search syntax.

        Example queries: ``assignee:me status:open``, ``color:red``, ``"login bug"``.
        """
        return await run(request_headers(), "search_tasks", project_id=project_id, query=query)

    # ---- Tasks (write) ----------------------------------------------------

    @mcp.tool
    async def create_task(
        project_id: int,
        title: str,
        description: str | None = None,
        column_id: int | None = None,
        owner_id: int | None = None,
        date_due: str | None = None,
        priority: int | None = None,
    ) -> Any:
        """Create a task in a project. Returns the new task id (0 on failure).

        Args:
            project_id: Target project.
            title: Task title (required).
            description: Markdown body.
            column_id: Column to place the task in (defaults to the first column).
            owner_id: Assignee user id.
            date_due: Due date, ``YYYY-MM-DD`` or a unix timestamp.
            priority: Numeric priority.
        """
        params = _clean(
            project_id=project_id,
            title=title,
            description=description,
            column_id=column_id,
            owner_id=owner_id,
            date_due=date_due,
            priority=priority,
        )
        return await run(request_headers(), "create_task", **params)

    @mcp.tool
    async def update_task(
        id: int,
        title: str | None = None,
        description: str | None = None,
        owner_id: int | None = None,
        date_due: str | None = None,
        priority: int | None = None,
    ) -> Any:
        """Update fields on an existing task. Only provided fields change."""
        params = _clean(
            id=id,
            title=title,
            description=description,
            owner_id=owner_id,
            date_due=date_due,
            priority=priority,
        )
        return await run(request_headers(), "update_task", **params)

    @mcp.tool
    async def move_task(
        project_id: int,
        task_id: int,
        column_id: int,
        position: int = 1,
        swimlane_id: int = 1,
    ) -> Any:
        """Move a task to a column/position/swimlane on its board.

        ``position`` is 1-based within the column. Use :func:`get_board` to find
        column and swimlane ids.
        """
        return await run(
            request_headers(),
            "move_task_position",
            project_id=project_id,
            task_id=task_id,
            column_id=column_id,
            position=position,
            swimlane_id=swimlane_id,
        )

    # ---- Comments ---------------------------------------------------------

    @mcp.tool
    async def get_task_comments(task_id: int) -> Any:
        """Get all comments on a task."""
        return await run(request_headers(), "get_all_comments", task_id=task_id)

    @mcp.tool
    async def add_comment(task_id: int, content: str, user_id: int | None = None) -> Any:
        """Add a comment to a task, authored by the calling user.

        If ``user_id`` is omitted, the authenticated user's id is used so the
        comment is attributed correctly.
        """
        headers = request_headers()
        if user_id is None:
            me = await run(headers, "get_me")
            user_id = me["id"]
        return await run(
            headers, "create_comment", task_id=task_id, user_id=user_id, content=content
        )
