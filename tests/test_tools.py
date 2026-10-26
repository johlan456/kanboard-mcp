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
    monkeypatch.setattr(tools, "request_headers", dict)

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


async def _call_tool(monkeypatch, tool_name: str, /, **tool_args):
    """Invoke a tool with a stubbed ``run`` and return (method, params) it sent."""
    captured = {}

    async def fake_run(headers, method, **params):
        captured["method"] = method
        captured["params"] = params
        return 42

    monkeypatch.setattr(tools, "run", fake_run)
    monkeypatch.setattr(tools, "request_headers", dict)

    mcp = FastMCP("test")
    tools.register_tools(mcp)
    tool = await mcp.get_tool(tool_name)
    result = await tool.fn(**tool_args)
    return captured["method"], captured["params"], result


@pytest.mark.anyio
async def test_create_project_team(monkeypatch):
    method, params, result = await _call_tool(
        monkeypatch, "create_project", name="Infra", identifier="INFRA"
    )
    assert method == "create_project"
    assert params == {"name": "Infra", "identifier": "INFRA"}
    assert result == 42


@pytest.mark.anyio
async def test_create_project_private(monkeypatch):
    method, params, _ = await _call_tool(
        monkeypatch, "create_project", name="My notes", private=True
    )
    assert method == "create_my_private_project"
    assert params == {"name": "My notes"}


@pytest.mark.anyio
async def test_create_subtask_drops_unset_params(monkeypatch):
    method, params, _ = await _call_tool(
        monkeypatch, "create_subtask", task_id=7, title="Write docs"
    )
    assert method == "create_subtask"
    assert params == {"task_id": 7, "title": "Write docs"}


@pytest.mark.anyio
async def test_update_subtask_status_only(monkeypatch):
    method, params, _ = await _call_tool(
        monkeypatch, "update_subtask", id=3, task_id=7, status=2
    )
    assert method == "update_subtask"
    assert params == {"id": 3, "task_id": 7, "status": 2}


@pytest.mark.anyio
async def test_get_task_subtasks(monkeypatch):
    method, params, _ = await _call_tool(monkeypatch, "get_task_subtasks", task_id=7)
    assert method == "get_all_subtasks"
    assert params == {"task_id": 7}


# (tool name, call args, expected JSON-RPC method, expected params sent)
PASSTHROUGH_CASES = [
    ("get_my_dashboard", {}, "get_my_dashboard", {}),
    ("get_my_overdue_tasks", {}, "get_my_overdue_tasks", {}),
    ("get_assignable_users", {"project_id": 1}, "get_assignable_users", {"project_id": 1}),
    ("get_project_activity", {"project_id": 1}, "get_project_activity", {"project_id": 1}),
    (
        "add_column",
        {"project_id": 1, "title": "Review"},
        "add_column",
        {"project_id": 1, "title": "Review"},
    ),
    (
        "update_column",
        {"column_id": 4, "title": "Review", "task_limit": 3},
        "update_column",
        {"column_id": 4, "title": "Review", "task_limit": 3},
    ),
    (
        "add_swimlane",
        {"project_id": 1, "name": "Team B"},
        "add_swimlane",
        {"project_id": 1, "name": "Team B"},
    ),
    ("get_task_files", {"task_id": 5}, "get_all_task_files", {"task_id": 5}),
    ("close_task", {"task_id": 5}, "close_task", {"task_id": 5}),
    ("open_task", {"task_id": 5}, "open_task", {"task_id": 5}),
    (
        "move_task_to_project",
        {"task_id": 5, "project_id": 2},
        "move_task_to_project",
        {"task_id": 5, "project_id": 2},
    ),
    (
        "duplicate_task_to_project",
        {"task_id": 5, "project_id": 2, "column_id": 9},
        "duplicate_task_to_project",
        {"task_id": 5, "project_id": 2, "column_id": 9},
    ),
    ("get_project_tags", {"project_id": 1}, "get_tags_by_project", {"project_id": 1}),
    ("get_task_tags", {"task_id": 5}, "get_task_tags", {"task_id": 5}),
    (
        "set_task_tags",
        {"project_id": 1, "task_id": 5, "tags": ["urgent", "backend"]},
        "set_task_tags",
        {"project_id": 1, "task_id": 5, "tags": ["urgent", "backend"]},
    ),
    ("get_all_categories", {"project_id": 1}, "get_all_categories", {"project_id": 1}),
    (
        "create_category",
        {"project_id": 1, "name": "Bug"},
        "create_category",
        {"project_id": 1, "name": "Bug"},
    ),
    (
        "update_comment",
        {"id": 8, "content": "edited"},
        "update_comment",
        {"id": 8, "content": "edited"},
    ),
    ("list_link_types", {}, "get_all_links", {}),
    ("get_task_links", {"task_id": 5}, "get_all_task_links", {"task_id": 5}),
    (
        "create_task_link",
        {"task_id": 5, "opposite_task_id": 6, "link_id": 2},
        "create_task_link",
        {"task_id": 5, "opposite_task_id": 6, "link_id": 2},
    ),
]


@pytest.mark.anyio
@pytest.mark.parametrize("tool_name,args,method,params", PASSTHROUGH_CASES)
async def test_tool_sends_expected_rpc(monkeypatch, tool_name, args, method, params):
    got_method, got_params, _ = await _call_tool(monkeypatch, tool_name, **args)
    assert got_method == method
    assert got_params == params


@pytest.mark.anyio
async def test_create_task_with_tags_and_category(monkeypatch):
    method, params, _ = await _call_tool(
        monkeypatch,
        "create_task",
        project_id=1,
        title="Fix login",
        tags=["bug"],
        category_id=2,
    )
    assert method == "create_task"
    assert params == {
        "project_id": 1,
        "title": "Fix login",
        "tags": ["bug"],
        "category_id": 2,
    }


@pytest.fixture
def anyio_backend():
    return "asyncio"
