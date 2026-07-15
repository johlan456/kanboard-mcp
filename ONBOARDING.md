# Kanboard MCP — Connect Claude to our Kanban board

Connect Claude Code or Claude Desktop to our Kanboard instance so you can ask
Claude to list your tasks, create and move cards, add comments, and search
boards — all as *you*. Every action runs under your own Kanboard account, so
permissions apply normally and cards show you as the author.

**Server URL:** `https://mcp.agileworksgroup.ai/mcp`

Setup takes about 3 minutes.

## Step 1 — Get your personal API token

1. Log in at [kanban.agileworksgroup.ai](https://kanban.agileworksgroup.ai) (Google sign-in as usual).
2. Note your **username** — click your avatar → **My profile**. It's the short
   name shown there (e.g. `johlan`), **not your email address**.
3. Still in your profile, open the **API** section and click
   **Generate a new token**. Copy it somewhere safe — you'll paste it once below.

This token is personal. Treat it like a password: don't share it or commit it
to git. You can revoke/regenerate it any time from the same page.

## Step 2 — Add the server to Claude

### Claude Code (CLI)

Run this once, substituting your username and token:

```bash
claude mcp add --transport http --scope user kanboard-awg https://mcp.agileworksgroup.ai/mcp \
  --header "X-Kanboard-Username: <your-username>" \
  --header "X-Kanboard-Token: <your-token>"
```

`--scope user` stores it in `~/.claude.json` (your machine only, never in a repo).
Restart any open Claude Code sessions afterwards.

### Claude Desktop

Open **Settings → Developer → Edit Config** (`claude_desktop_config.json`) and
add under `mcpServers` (note: no space after the `:` in the header values —
this avoids an argument-splitting quirk on Windows):

```json
{
  "mcpServers": {
    "kanboard-awg": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote", "https://mcp.agileworksgroup.ai/mcp",
        "--header", "X-Kanboard-Username:<your-username>",
        "--header", "X-Kanboard-Token:<your-token>"
      ]
    }
  }
}
```

Requires Node.js installed. Restart Claude Desktop afterwards.

## Step 3 — Verify

Ask Claude: **"Use the kanboard whoami tool — who am I?"**

You should see your own name and role. Then try
**"List my Kanboard projects"** — you'll only see boards you're a member of.

## What Claude can do

`whoami` · `list_my_projects` · `get_project` · `get_board` · `get_task` ·
`search_tasks` · `create_task` · `update_task` · `move_task` ·
`get_task_comments` · `add_comment`

There is deliberately **no delete** tool.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `HTTP Error 401: Unauthorized` | Username must be your Kanboard username (My profile), not your email. If it looks right, regenerate the token and re-add — a stray space in the paste is the usual culprit. |
| Changed headers but still 401 | Restart Claude Code / Desktop — header changes only load on startup. |
| Tools don't appear at all | `claude mcp list` should show `kanboard-awg`. Re-run the add command, restart. |

## How it works (for the curious)

The MCP server is a thin, stateless bridge to Kanboard's API. It stores no
credentials — your username + token travel with each request and are forwarded
straight to Kanboard, which enforces your normal permissions. Compromise of
the bridge exposes nothing; your token is revocable by you at any time.

Questions → Johlan.
