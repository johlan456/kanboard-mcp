# kanboard-mcp

A multi-tenant [MCP](https://modelcontextprotocol.io) server for **self-hosted
Kanboard**. One deployed instance serves a whole team: each request carries the
caller's own Kanboard credential, so every action runs as that user — with their
permissions and their authorship. The server is stateless and stores no tokens.

Built on the official [`kanboard`](https://github.com/kanboard/python-api-client)
API client and [FastMCP](https://gofastmcp.com).

## Why this exists

- The official `kanboard.io/api/mcp` is **cloud-only** — it can't talk to a
  self-hosted instance.
- Self-hosted Kanboard ships **no MCP endpoint**, only the JSON-RPC API.
- Existing community bridges are **single-tenant stdio** — one shared identity,
  not suitable for a team.

This server fills that gap: central, HTTP, per-user.

## How auth works

Every request must carry a Kanboard credential. Use each person's **personal API
token** (Kanboard → your profile → *API*) with their real username, so actions
respect that user's permissions. Three accepted schemes:

| Scheme | Header(s) |
|---|---|
| Explicit | `X-Kanboard-Username: <user>` + `X-Kanboard-Token: <token>` |
| HTTP Basic | `Authorization: Basic base64("<user>:<token>")` |
| Bearer | `Authorization: Bearer <user>:<token>` |

> The app-wide `jsonrpc` token works too but is admin-level and bypasses
> per-user permissions — don't hand it to end users.

## Run locally

```bash
uv sync
cp .env.example .env        # set KANBOARD_URL
uv run kanboard-mcp         # serves http://127.0.0.1:8000/mcp
```

## Run with Docker

```bash
docker build -t kanboard-mcp .
docker run --rm -p 8000:8000 -e KANBOARD_URL=https://kanboard.example.com/jsonrpc.php kanboard-mcp
```

Front it with TLS (reverse proxy or tunnel); keep the container bound to the
proxy only. The container ships a Docker `HEALTHCHECK` against `GET /health`
(unauthenticated liveness probe — returns `{"status": "ok", ...}`).

### Cloudflare Tunnel

Publish the container through `cloudflared` so nothing is exposed directly;
credentials in headers then always travel over TLS to Cloudflare's edge:

```yaml
# cloudflared config.yml ingress entry
- hostname: kanboard-mcp.example.com
  service: http://127.0.0.1:8000
```

Bind the published port to loopback (`-p 127.0.0.1:8000:8000`) so only the
tunnel can reach it.

## Connect a client

**Claude Code**

```bash
claude mcp add --transport http kanboard https://kanboard-mcp.example.com/mcp \
  --header "Authorization: Bearer <your-username>:<your-personal-token>"
```

**Claude Desktop** — add a remote MCP server with the same URL and header.

Verify with the `whoami` tool — it should return *your* Kanboard user.

## Configuration

| Env var | Required | Default | Description |
|---|---|---|---|
| `KANBOARD_URL` | ✅ | — | Kanboard JSON-RPC endpoint (`.../jsonrpc.php`) |
| `HOST` | | `127.0.0.1` | Bind address |
| `PORT` | | `8000` | Bind port |
| `KANBOARD_TIMEOUT` | | `30` | Per-request timeout (s) |
| `LOG_LEVEL` | | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |

No token is ever read from the environment — credentials are per-request only.

## Tools

36 tools covering day-to-day task management, always as the calling user:

- **Me** — `whoami`, `get_my_dashboard`, `get_my_overdue_tasks`
- **Projects** — `list_my_projects`, `create_project`, `get_project`,
  `get_board`, `get_assignable_users`, `get_project_activity`
- **Board structure** — `add_column`, `update_column`, `add_swimlane`
- **Tasks** — `get_task`, `search_tasks`, `get_task_files`, `create_task`,
  `update_task`, `move_task`, `close_task`, `open_task`,
  `move_task_to_project`, `duplicate_task_to_project`
- **Tags & categories** — `get_project_tags`, `get_task_tags`, `set_task_tags`,
  `get_all_categories`, `create_category`
- **Subtasks** — `get_task_subtasks`, `create_subtask`, `update_subtask`
- **Comments** — `get_task_comments`, `add_comment`, `update_comment`
- **Task links** — `list_link_types`, `get_task_links`, `create_task_link`

Deliberate omissions: no `remove*`/delete tools, and no binary file transfer
(attachments can be listed, not uploaded or downloaded). Adding more is a few
lines each — the underlying client exposes every Kanboard API method by
dynamic dispatch. See `src/kanboard_mcp/tools.py`.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check
```

## License

MIT
