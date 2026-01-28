import argparse
import asyncio
import json
import os
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

DEFAULT_URL = "http://127.0.0.1:8000/mcp/streamable_http"
DEFAULT_MODEL = "gpt-4o-mini"


def _parse_args() -> argparse.Namespace:
    # CLI options for server endpoint and routing behavior
    parser = argparse.ArgumentParser(description="Route user input to MCP tools")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"MCP streamable HTTP endpoint (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"LLM model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENAI_BASE_URL", ""),
        help="OpenAI-compatible base URL (or set OPENAI_BASE_URL)",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="User input to route",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=3,
        help="Max tool-calling steps (default: 3)",
    )
    return parser.parse_args()


def _ensure_openai_key() -> None:
    # Required by OpenAI-compatible clients (including proxies)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")


def _coerce_tool_args(raw_args: Any) -> dict:
    # Normalize tool args into a dict for tool invocation
    if raw_args is None:
        return {}
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return {}
    return {}


async def _run(
    url: str, model: str, user_input: str, max_steps: int, base_url: str
) -> None:
    _ensure_openai_key()

    # Load MCP tools via LangChain MCP adapters
    client = MultiServerMCPClient(
        {
            "mcp_server": {
                "transport": "http",
                "url": url,
            }
        }
    )
    tools = await client.get_tools(server_name="mcp_server")
    tool_map = {tool.name: tool for tool in tools}

    # Bind tools so the model can choose and call them
    llm = ChatOpenAI(model=model, temperature=0, base_url=base_url or None)
    llm_with_tools = llm.bind_tools(tools)

    # Simple loop: model decides whether to call tools, then we execute calls
    messages = [HumanMessage(content=user_input)]

    for _ in range(max_steps):
        ai_msg = await llm_with_tools.ainvoke(messages)
        messages.append(ai_msg)

        tool_calls = getattr(ai_msg, "tool_calls", None) or []
        if not tool_calls:
            print(ai_msg.content)
            return

        for call in tool_calls:
            name = call.get("name")
            tool = tool_map.get(name)
            if tool is None:
                result = f"Tool '{name}' not found"
            else:
                tool_args = _coerce_tool_args(call.get("args"))
                result = await tool.ainvoke(tool_args)
            messages.append(
                ToolMessage(content=str(result), tool_call_id=call.get("id"))
            )

    print("Max steps reached without final response.")


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(_run(args.url, args.model, args.input, args.max_steps, args.base_url))
