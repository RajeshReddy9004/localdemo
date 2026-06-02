# DevAssist MCP 🤖

> A Django backend made **AI-native** with the **Model Context Protocol (MCP)** — plus a custom AI agent that drives it.

DevAssist is a task & knowledge manager built in Django, exposed to AI assistants
(Claude Desktop, IDEs, or the included custom agent) through an MCP server. It
demonstrates the **full MCP picture**: a real backend, an MCP **server** that
exposes it, *and* a custom MCP **host/agent** that consumes it.

---

## ✨ Why this project is interesting

Most MCP demos stop at a toy server. This one shows the parts that matter in a
real product:

- **One backend, two front doors** — humans use Django Admin + a DRF REST API;
  AI uses MCP. Both call a single shared `services.py`, so they never drift.
- **All three MCP primitives** — Tools, Resources, *and* Prompts.
- **You build the host too** — a custom Anthropic-SDK agent that discovers the
  server's tools and runs a real tool-calling loop.
- **Correct async/Django integration** — sync ORM safely driven from async MCP
  handlers via `sync_to_async`.
- **Production polish** — tests, Docker, `.env` config, and a Claude Desktop
  integration you can demo live.

---

## 🧠 What is MCP (30-second version)

The **Model Context Protocol** is an open standard (Anthropic, 2024) that
standardizes how AI apps connect to tools and data — "USB-C for AI." A **host**
(the AI app) runs a **client** that connects to **servers**, which expose:

| Primitive | What it is | Example here |
|-----------|------------|--------------|
| **Tools** | Functions the model can call | `create_task`, `search_github` |
| **Resources** | Data the model can read | `notes://all`, `note://{id}` |
| **Prompts** | Reusable prompt templates | `daily_standup` |

---

## 🏗️ Architecture

```
                         ┌──────────────────────────────┐
   Human (browser) ────▶ │ Django Admin / DRF REST API   │ ┐
                         └──────────────────────────────┘ │
                                                           ├─▶ core/services.py ─▶ ORM ─▶ SQLite
                         ┌──────────────────────────────┐ │
   AI host ───MCP──────▶ │ mcp_server/server.py (FastMCP) │ ┘
   (Claude Desktop /     │   tools · resources · prompts │
    agent/client.py)     └──────────────────────────────┘
```

See [`docs/architecture.md`](docs/architecture.md) for the full design rationale.

---

## 📂 Project layout

```
devassist-mcp/
├── devassist/            # Django project (settings, urls, wsgi/asgi)
├── core/                 # Django app: models, admin, REST API
│   ├── models.py         #   Project, Task, Note
│   ├── services.py       #   ← shared business logic (API + MCP both use this)
│   ├── views.py          #   DRF viewsets
│   └── tests.py          #   unit tests for the services layer
├── mcp_server/
│   └── server.py         # ← the MCP server (tools / resources / prompts)
├── agent/
│   └── client.py         # ← custom MCP host: an Anthropic-SDK agent loop
├── manage.py
├── requirements.txt
├── Dockerfile / docker-compose.yml
└── claude_desktop_config.example.json
```

---

## 🚀 Quick start

### 1. Setup

```bash
cd devassist-mcp

# create & activate a virtual env
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# configure environment
cp .env.example .env        # Windows: copy .env.example .env
# edit .env and set ANTHROPIC_API_KEY (only needed for the agent)
```

### 2. Initialize the database

```bash
python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser   # for the admin
```

### 3. Run the Django backend (humans)

```bash
python manage.py runserver
```

- Admin: http://127.0.0.1:8000/admin/
- REST API: http://127.0.0.1:8000/api/tasks/

### 4. Run the MCP server + custom agent (AI)

In one terminal, you can sanity-check the server with the official inspector:

```bash
mcp dev mcp_server/server.py
```

Then talk to it through a bundled agent. **The MCP server is model-agnostic** —
pick whichever provider you have a key for:

```bash
# Gemini (free tier — set GEMINI_API_KEY in .env)
python agent/gemini_client.py
python agent/gemini_client.py "Search GitHub for the top MCP repos, then save a note about them"

# Anthropic / Claude (set ANTHROPIC_API_KEY in .env)
python agent/client.py
python agent/client.py "Add a high-priority task to prep for system design interviews, then list my todos"
```

Each agent launches the MCP server for you, discovers its tools, and lets the
model call them in a loop. Swapping `gemini_client.py` ↔ `client.py` changes
*only the model* — the server is identical. That's the whole point of MCP.

---

## 🧪 Tests

```bash
python manage.py test
```

---

## 🖥️ Use it inside Claude Desktop (great for demos)

1. Install [Claude Desktop](https://claude.ai/download).
2. Open its config file:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
3. Merge in the `devassist` block from
   [`claude_desktop_config.example.json`](claude_desktop_config.example.json),
   using **absolute paths** to your venv's Python and to `mcp_server/server.py`.
4. Fully restart Claude Desktop. You'll see DevAssist's tools (🔨 icon) and can
   say things like *"Create a task to review my resume"* or *"Give me my daily standup."*

---

## 🛠️ What the server exposes

**Tools:** `create_task`, `list_tasks`, `update_task`, `complete_task`,
`delete_task`, `create_note`, `search_notes`, `search_github`, `fetch_url`

**Resources:** `notes://all` (index), `note://{id}` (single note)

**Prompts:** `daily_standup`, `summarize_open_tasks`

---

## 🐳 Docker

```bash
docker compose up --build      # Django backend at http://localhost:8000
```

---

## 🗣️ How to talk about this in an interview

- *"I exposed a Django backend to AI over MCP without duplicating logic — the
  REST API and the MCP server share one services layer."*
- *"I implemented all three MCP primitives and built a custom host with the
  Anthropic SDK, so I understand both ends of the protocol."*
- *"The tricky part was driving Django's synchronous ORM from MCP's async
  handlers; I solved it cleanly with `sync_to_async`."*

---

## 📚 Learn more

- MCP docs: https://modelcontextprotocol.io
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Anthropic API: https://docs.anthropic.com

## License

MIT — use it freely in your portfolio.
