"""
DevAssist MCP server.

Exposes a Django backend to any MCP-compatible AI host (Claude Desktop, an IDE,
or our own agent in ``agent/client.py``) through the three MCP primitives:

    * Tools     – actions the model can take   (create_task, search_github, ...)
    * Resources – data the model can read      (notes://all, note://{id})
    * Prompts   – reusable prompt templates     (daily_standup, ...)

Run directly over stdio:

    python mcp_server/server.py

Or inspect it interactively with the official MCP inspector:

    mcp dev mcp_server/server.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# 1. Bootstrap Django BEFORE importing anything that touches the ORM.
#    We add the project root to sys.path so this works no matter the CWD.
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "devassist.settings")

import django  # noqa: E402

django.setup()

# --------------------------------------------------------------------------- #
# 2. Now the rest of the imports are safe.
# --------------------------------------------------------------------------- #
import httpx  # noqa: E402
from asgiref.sync import sync_to_async  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from core import services  # noqa: E402

mcp = FastMCP("devassist")

# The ORM is synchronous; MCP handlers run in an async event loop. ``sync_to_async``
# pushes each ORM call onto a worker thread so Django stays happy.
aio = sync_to_async


# =========================================================================== #
# TOOLS — actions the model can take
# =========================================================================== #
@mcp.tool()
async def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    project: str | None = None,
    due_date: str | None = None,
) -> dict:
    """Create a new task.

    Args:
        title: Short title of the task.
        description: Optional longer description.
        priority: One of "low", "medium", "high".
        project: Optional project name; created automatically if it doesn't exist.
        due_date: Optional ISO date, e.g. "2026-07-01".
    """
    return await aio(services.create_task)(
        title=title,
        description=description,
        priority=priority,
        project_name=project,
        due_date=due_date,
    )


@mcp.tool()
async def list_tasks(status: str | None = None, project: str | None = None) -> list[dict]:
    """List tasks, optionally filtered.

    Args:
        status: Optional filter — "todo", "in_progress", or "done".
        project: Optional project name to filter by.
    """
    return await aio(services.list_tasks)(status=status, project_name=project)


@mcp.tool()
async def update_task(
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_date: str | None = None,
) -> dict | str:
    """Update fields on an existing task. Only provided fields change."""
    result = await aio(services.update_task)(
        task_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
    )
    return result or f"No task found with id {task_id}."


@mcp.tool()
async def complete_task(task_id: int) -> dict | str:
    """Mark a task as done."""
    result = await aio(services.complete_task)(task_id)
    return result or f"No task found with id {task_id}."


@mcp.tool()
async def delete_task(task_id: int) -> str:
    """Permanently delete a task."""
    ok = await aio(services.delete_task)(task_id)
    return f"Deleted task {task_id}." if ok else f"No task found with id {task_id}."


@mcp.tool()
async def create_note(title: str, content: str, tags: str = "") -> dict:
    """Save a knowledge note.

    Args:
        title: Note title.
        content: Note body.
        tags: Optional comma-separated tags.
    """
    return await aio(services.create_note)(title=title, content=content, tags=tags)


@mcp.tool()
async def search_notes(query: str) -> list[dict]:
    """Full-text-ish search across note titles, content, and tags."""
    return await aio(services.search_notes)(query)


@mcp.tool()
async def search_github(query: str, limit: int = 5) -> list[dict]:
    """Search public GitHub repositories.

    Args:
        query: Search query, e.g. "model context protocol".
        limit: Max number of repositories to return (1–10).
    """
    limit = max(1, min(limit, 10))
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "sort": "stars", "per_page": limit},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "full_name": item["full_name"],
            "stars": item["stargazers_count"],
            "description": item.get("description"),
            "url": item["html_url"],
            "language": item.get("language"),
        }
        for item in data.get("items", [])
    ]


@mcp.tool()
async def fetch_url(url: str, max_chars: int = 4000) -> str:
    """Fetch a web page and return its (truncated) text content.

    Useful for letting the model read documentation or an article you point it at.
    """
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "DevAssist-MCP/1.0"})
        resp.raise_for_status()
        text = resp.text
    return text[:max_chars] + ("\n…[truncated]" if len(text) > max_chars else "")


# =========================================================================== #
# RESOURCES — data the model can read
# =========================================================================== #
@mcp.resource("notes://all")
async def all_notes_resource() -> str:
    """A bulleted index of every saved note."""
    notes = await aio(services.list_notes)()
    if not notes:
        return "No notes saved yet."
    return "\n".join(f"- [{n['id']}] {n['title']} (tags: {', '.join(n['tags'])})" for n in notes)


@mcp.resource("note://{note_id}")
async def note_resource(note_id: str) -> str:
    """The full content of a single note by id."""
    note = await aio(services.get_note)(int(note_id))
    if not note:
        return f"No note found with id {note_id}."
    return f"# {note['title']}\nTags: {', '.join(note['tags'])}\n\n{note['content']}"


# =========================================================================== #
# PROMPTS — reusable templates the user can invoke
# =========================================================================== #
@mcp.prompt()
def daily_standup() -> str:
    """Generate a daily standup summary from current tasks."""
    return (
        "Using the list_tasks tool, give me a daily standup. "
        "Group the output into three sections: 'Done', 'In Progress', and "
        "'To Do (Up Next)'. Within each section, sort by priority (high first). "
        "End with one sentence suggesting what I should focus on today."
    )


@mcp.prompt()
def summarize_open_tasks(project: str = "") -> str:
    """Summarize open tasks, optionally scoped to a project."""
    scope = f" for the '{project}' project" if project else ""
    return (
        f"Call list_tasks (status='todo'){scope} and summarize my open work{scope} "
        "in 3–5 bullet points, highlighting anything high priority or overdue."
    )


if __name__ == "__main__":
    # Default transport is stdio — exactly what Claude Desktop and our agent expect.
    mcp.run()
