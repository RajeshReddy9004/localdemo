"""
DevAssist agent — Gemini edition (a custom MCP *host*).

Identical job to ``agent/client.py`` but powered by Google Gemini instead of
Anthropic. This is the whole promise of MCP in action: the **server doesn't
change at all** — only the host/model does. Gemini's SDK can take an MCP
``ClientSession`` directly as a tool and auto-calls the server's tools for us.

Usage:
    python agent/gemini_client.py
    python agent/gemini_client.py "Add a high-priority task to prep system design"

Requires GEMINI_API_KEY in your environment (or .env). Free tier works fine.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Windows consoles default to cp1252, which can't print emoji. Force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
SYSTEM_PROMPT = (
    "You are DevAssist, a helpful productivity assistant. You manage the user's "
    "tasks and notes and can research GitHub and the web. Prefer using the "
    "available tools over guessing. Be concise."
)

SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=[str(BASE_DIR / "mcp_server" / "server.py")],
)


async def ask(client: genai.Client, session: ClientSession, prompt: str) -> str:
    """Send one request; Gemini auto-calls MCP tools on the session as needed."""
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            tools=[session],  # ← the MCP session itself; the SDK handles tool calls
        ),
    )
    return response.text or "(no text response)"


async def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("ERROR: set GEMINI_API_KEY (e.g. in your .env file) first.")

    client = genai.Client(api_key=api_key)
    one_shot = " ".join(sys.argv[1:]).strip()

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            print(f"Connected to DevAssist MCP server. {len(tools)} tools available (via Gemini).\n")

            if one_shot:
                print(f"🤖 {await ask(client, session, one_shot)}\n")
                return

            print("Type a request, or 'quit' to exit.\n")
            while True:
                try:
                    user_input = input("you ▸ ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if user_input.lower() in {"quit", "exit", "q"}:
                    break
                if user_input:
                    print(f"\n🤖 {await ask(client, session, user_input)}\n")


if __name__ == "__main__":
    asyncio.run(main())
