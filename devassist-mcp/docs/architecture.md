# Architecture

## Why this design

The interesting idea in DevAssist is **one backend, two front doors**:

- **Humans** reach the data through Django Admin + the DRF REST API.
- **AI** reaches the same data through the MCP server.

Both front doors call into a single `core/services.py` layer, so behavior can
never diverge. Add a feature once in `services.py` and it shows up in the API
and to the AI simultaneously.

```
                         ┌─────────────────────────────┐
   Human (browser) ────▶ │ Django Admin / DRF REST API  │ ┐
                         └─────────────────────────────┘ │
                                                          ├─▶ core/services.py ─▶ ORM ─▶ SQLite
                         ┌─────────────────────────────┐ │
   AI host ───MCP──────▶ │ mcp_server/server.py (FastMCP)│ ┘
   (Claude Desktop /     │  tools · resources · prompts │
    agent/client.py)     └─────────────────────────────┘
```

## Request flow (AI path)

1. The host (Claude Desktop or `agent/client.py`) spawns `server.py` and speaks
   MCP over **stdio** (newline-delimited JSON-RPC).
2. On `initialize`, the host discovers tools, resources, and prompts.
3. When the model decides to act, the host sends `tools/call`; FastMCP routes it
   to the matching `@mcp.tool()` function.
4. The tool calls `services.*`. Because the ORM is synchronous and the handler
   is async, `sync_to_async` runs the DB work on a worker thread.
5. The result is serialized to JSON and streamed back to the model.

## Key design decisions

| Decision | Why |
|---|---|
| Shared `services.py` | Single source of truth for API + MCP; easy to test. |
| Services return dicts, not ORM objects | Avoids lazy DB hits inside the async event loop; clean JSON for MCP. |
| `sync_to_async` wrappers | Correct, production-grade way to use the sync ORM from async MCP. |
| stdio transport | Zero network setup; the standard for local MCP servers. |
| Building our own host (`agent/`) | Demonstrates *both* sides of the protocol, not just a server. |

## Where to take it next

- Swap SQLite for Postgres (change one settings block).
- Add an HTTP/SSE transport so the server can run remotely.
- Add auth + per-user task isolation (tie `Task` to `request.user`).
- Add a `resource` that streams a task as live-updating JSON.
