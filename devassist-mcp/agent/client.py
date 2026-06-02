"""
DevAssist agent — a custom MCP *host*.

This is the half most people skip. It:
    1. Launches the MCP server as a subprocess and connects over stdio.
    2. Discovers the server's tools and translates them into Anthropic tool specs.
    3. Runs an agentic loop with Claude: the model decides which MCP tools to
       call, we execute them against the server, feed results back, and repeat
       until the model produces a final answer.

Usage:
    python agent/client.py
    python agent/client.py "Add a high-priority task to prep system design"

Requires ANTHROPIC_API_KEY in your environment (or .env).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Windows consoles default to cp1252, which can't print emoji. Force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 2048
SYSTEM_PROMPT = (
    "You are DevAssist, a helpful productivity assistant. You manage the user's "
    "tasks and notes and can research GitHub and the web. Prefer using the "
    "available tools over guessing. Be concise."
)

# How to start the MCP server. We reuse the same Python interpreter.
SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=[str(BASE_DIR / "mcp_server" / "server.py")],
)


def _mcp_tools_to_anthropic(mcp_tools) -> list[dict]:
    """Translate MCP tool definitions into the Anthropic `tools` schema."""
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        }
        for tool in mcp_tools
    ]


async def run_agent(session: ClientSession, anthropic: Anthropic, user_input: str) -> None:
    tool_list = (await session.list_tools()).tools
    tools = _mcp_tools_to_anthropic(tool_list)

    messages: list[dict] = [{"role": "user", "content": user_input}]

    while True:
        response = anthropic.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Print any text the model emitted this turn.
        for block in response.content:
            if block.type == "text":
                print(f"\n🤖 {block.text}\n")

        if response.stop_reason != "tool_use":
            return  # model is done

        # Execute every tool the model asked for, then loop back with the results.
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"   ↳ calling tool: {block.name}({block.input})")
            result = await session.call_tool(block.name, block.input)
            text = "".join(c.text for c in result.content if c.type == "text")
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": text,
                    "is_error": bool(result.isError),
                }
            )
        messages.append({"role": "user", "content": tool_results})


async def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ERROR: set ANTHROPIC_API_KEY (e.g. in your .env file) first.")

    anthropic = Anthropic()
    one_shot = " ".join(sys.argv[1:]).strip()

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            print(f"Connected to DevAssist MCP server. {len(tools)} tools available.")

            if one_shot:
                await run_agent(session, anthropic, one_shot)
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
                    await run_agent(session, anthropic, user_input)


if __name__ == "__main__":
    asyncio.run(main())
