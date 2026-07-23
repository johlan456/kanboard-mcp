"""Kanboard tool surface exposed over MCP.

Every tool runs as the calling employee: it reads the per-request credential
from the incoming HTTP headers and forwards the JSON-RPC call under that
identity. Kanboard then applies that user's permissions and records authorship.

The surface covers day-to-day task management for a project member: projects
and boards, tasks (including close/reopen, cross-project move/duplicate),
subtasks, comments, tags, categories, task links, and the caller's own
dashboard. Deliberate omissions: destructive ``remove*`` methods (no delete
tools) and binary file transfer (attachments can be listed, not up/downloaded).
Because the underlying ``kanboard`` client exposes *every* API method by
dynamic dispatch, adding more is a few lines each — expand as the team needs.
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

    @mcp.tool
    async def get_my_dashboard() -> Any:
        """Get the authenticated user's dashboard: their open tasks and subtasks
        across all projects they belong to."""
        return await run(request_headers(), "get_my_dashboard")

    @mcp.tool
    async def get_my_overdue_tasks() -> Any:
        """List the authenticated user's overdue tasks across all projects."""
        return await run(request_headers(), "get_my_overdue_tasks")

    # ---- Projects ---------------------------------------------------------

    @mcp.tool
    async def create_project(
        name: str,
        description: str | None = None,
        identifier: str | None = None,
        private: bool = False,
    ) -> Any:
        """Create a new project (every project has its own board).

        Returns the new project id (false/0 on failure). The board starts with
        Kanboard's default columns: Backlog, Ready, Work in progress, Done.

        Args:
            name: Project name (required).
            description: Markdown description.
            identifier: Optional short alphanumeric code (e.g. ``INFRA``).
            private: Create a personal project visible only to the caller.
                Team projects (the default) may require a manager/admin role —
                Kanboard enforces this and returns an error otherwise.
        """
        if private:
            # createMyPrivateProject is available to every role and takes no
            # identifier parameter.
            params = _clean(name=name, description=description)
            return await run(request_headers(), "create_my_private_project", **params)
        params = _clean(name=name, description=description, identifier=identifier)
        return await run(request_headers(), "create_project", **params)

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

    @mcp.tool
    async def get_assignable_users(project_id: int) -> Any:
        """List users who can be assigned tasks in a project, as ``{id: name}``.

        Use this to resolve a person's name to the ``owner_id``/``user_id``
        expected by the task and subtask tools.
        """
        return await run(request_headers(), "get_assignable_users", project_id=project_id)

    @mcp.tool
    async def get_project_activity(project_id: int) -> Any:
        """Get a project's recent activity stream (task events, comments, moves)."""
        return await run(request_headers(), "get_project_activity", project_id=project_id)

    # ---- Board structure ---------------------------------------------------

    @mcp.tool
    async def add_column(
        project_id: int,
        title: str,
        task_limit: int | None = None,
        description: str | None = None,
    ) -> Any:
        """Add a column to a project's board. Returns the new column id.

        Args:
            project_id: Target project.
            title: Column title (required).
            task_limit: Work-in-progress limit (0 or omitted = no limit).
            description: Markdown description.
        """
        params = _clean(
            project_id=project_id, title=title, task_limit=task_limit, description=description
        )
        return await run(request_headers(), "add_column", **params)

    @mcp.tool
    async def update_column(
        column_id: int,
        title: str,
        task_limit: int | None = None,
        description: str | None = None,
    ) -> Any:
        """Update a board column. ``title`` is required by the Kanboard API even
        when only changing other fields — pass the current title to keep it."""
        params = _clean(
            column_id=column_id, title=title, task_limit=task_limit, description=description
        )
        return await run(request_headers(), "update_column", **params)

    @mcp.tool
    async def add_swimlane(
        project_id: int, name: str, description: str | None = None
    ) -> Any:
        """Add a swimlane to a project's board. Returns the new swimlane id."""
        params = _clean(project_id=project_id, name=name, description=description)
        return await run(request_headers(), "add_swimlane", **params)

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

    @mcp.tool
    async def get_task_files(task_id: int) -> Any:
        """List a task's file attachments (name, size, date, uploader).

        Listing only — this connector does not transfer file contents.
        """
        return await run(request_headers(), "get_all_task_files", task_id=task_id)

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
        category_id: int | None = None,
        tags: list[str] | None = None,
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
            category_id: Category id (see :func:`get_all_categories`).
            tags: Tag names; unknown tags are created automatically.
        """
        params = _clean(
            project_id=project_id,
            title=title,
            description=description,
            column_id=column_id,
            owner_id=owner_id,
            date_due=date_due,
            priority=priority,
            category_id=category_id,
            tags=tags,
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
        category_id: int | None = None,
        tags: list[str] | None = None,
    ) -> Any:
        """Update fields on an existing task. Only provided fields change.

        ``tags`` replaces the task's full tag set when given.
        """
        params = _clean(
            id=id,
            title=title,
            description=description,
            owner_id=owner_id,
            date_due=date_due,
            priority=priority,
            category_id=category_id,
            tags=tags,
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

    @mcp.tool
    async def close_task(task_id: int) -> Any:
        """Close a task. Note this is separate from its board column — moving a
        card to Done does not close it."""
        return await run(request_headers(), "close_task", task_id=task_id)

    @mcp.tool
    async def open_task(task_id: int) -> Any:
        """Reopen a closed task."""
        return await run(request_headers(), "open_task", task_id=task_id)

    @mcp.tool
    async def move_task_to_project(
        task_id: int,
        project_id: int,
        swimlane_id: int | None = None,
        column_id: int | None = None,
        category_id: int | None = None,
        owner_id: int | None = None,
    ) -> Any:
        """Move a task to another project. Omitted fields fall back to the
        target project's defaults."""
        params = _clean(
            task_id=task_id,
            project_id=project_id,
            swimlane_id=swimlane_id,
            column_id=column_id,
            category_id=category_id,
            owner_id=owner_id,
        )
        return await run(request_headers(), "move_task_to_project", **params)

    @mcp.tool
    async def duplicate_task_to_project(
        task_id: int,
        project_id: int,
        swimlane_id: int | None = None,
        column_id: int | None = None,
        category_id: int | None = None,
        owner_id: int | None = None,
    ) -> Any:
        """Copy a task into another project. Returns the new task id."""
        params = _clean(
            task_id=task_id,
            project_id=project_id,
            swimlane_id=swimlane_id,
            column_id=column_id,
            category_id=category_id,
            owner_id=owner_id,
        )
        return await run(request_headers(), "duplicate_task_to_project", **params)

    # ---- Tags & categories -------------------------------------------------

    @mcp.tool
    async def get_project_tags(project_id: int) -> Any:
        """List the tags that exist in a project."""
        return await run(request_headers(), "get_tags_by_project", project_id=project_id)

    @mcp.tool
    async def get_task_tags(task_id: int) -> Any:
        """Get a task's tags, as ``{tag_id: name}``."""
        return await run(request_headers(), "get_task_tags", task_id=task_id)

    @mcp.tool
    async def set_task_tags(project_id: int, task_id: int, tags: list[str]) -> Any:
        """Replace a task's tags with the given names (pass ``[]`` to clear).

        Unknown tags are created in the project automatically.
        """
        return await run(
            request_headers(), "set_task_tags", project_id=project_id, task_id=task_id, tags=tags
        )

    @mcp.tool
    async def get_all_categories(project_id: int) -> Any:
        """List a project's categories."""
        return await run(request_headers(), "get_all_categories", project_id=project_id)

    @mcp.tool
    async def create_category(project_id: int, name: str) -> Any:
        """Create a category in a project. Returns the new category id."""
        return await run(
            request_headers(), "create_category", project_id=project_id, name=name
        )

    # ---- Subtasks ---------------------------------------------------------

    @mcp.tool
    async def get_task_subtasks(task_id: int) -> Any:
        """Get all subtasks of a task (id, title, status, assignee, time tracking).

        Subtask status: 0 = todo, 1 = in progress, 2 = done.
        """
        return await run(request_headers(), "get_all_subtasks", task_id=task_id)

    @mcp.tool
    async def create_subtask(
        task_id: int,
        title: str,
        user_id: int | None = None,
        time_estimated: int | None = None,
    ) -> Any:
        """Create a subtask on a task. Returns the new subtask id (false on failure).

        Args:
            task_id: Parent task.
            title: Subtask title (required).
            user_id: Assignee user id.
            time_estimated: Estimated hours.
        """
        params = _clean(
            task_id=task_id, title=title, user_id=user_id, time_estimated=time_estimated
        )
        return await run(request_headers(), "create_subtask", **params)

    @mcp.tool
    async def update_subtask(
        id: int,
        task_id: int,
        title: str | None = None,
        user_id: int | None = None,
        time_estimated: int | None = None,
        time_spent: int | None = None,
        status: int | None = None,
    ) -> Any:
        """Update fields on a subtask. Only provided fields change.

        Args:
            id: Subtask id (from :func:`get_task_subtasks`).
            task_id: Parent task id.
            title: New title.
            user_id: New assignee user id.
            time_estimated: Estimated hours.
            time_spent: Hours spent.
            status: 0 = todo, 1 = in progress, 2 = done.
        """
        params = _clean(
            id=id,
            task_id=task_id,
            title=title,
            user_id=user_id,
            time_estimated=time_estimated,
            time_spent=time_spent,
            status=status,
        )
        return await run(request_headers(), "update_subtask", **params)

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

    @mcp.tool
    async def update_comment(id: int, content: str) -> Any:
        """Replace the content of an existing comment.

        Kanboard permits editing your own comments; editing others' requires a
        manager/admin role and is enforced server-side.
        """
        return await run(request_headers(), "update_comment", id=id, content=content)

    # ---- Task links --------------------------------------------------------

    @mcp.tool
    async def list_link_types() -> Any:
        """List available task link types (e.g. "blocks", "duplicates").

        Use the returned ``id`` as ``link_id`` in :func:`create_task_link`.
        """
        return await run(request_headers(), "get_all_links")

    @mcp.tool
    async def get_task_links(task_id: int) -> Any:
        """Get a task's links to other tasks (relation, linked task, project)."""
        return await run(request_headers(), "get_all_task_links", task_id=task_id)

    @mcp.tool
    async def create_task_link(task_id: int, opposite_task_id: int, link_id: int) -> Any:
        """Link two tasks (e.g. task A *blocks* task B). Returns the link id.

        ``link_id`` is the relation type from :func:`list_link_types`; the
        inverse relation is created on the other task automatically.
        """
        return await run(
            request_headers(),
            "create_task_link",
            task_id=task_id,
            opposite_task_id=opposite_task_id,
            link_id=link_id,
        )
