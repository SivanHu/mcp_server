import argparse
import asyncio
import json

from langchain_mcp_adapters.client import MultiServerMCPClient

DEFAULT_URL = "http://127.0.0.1:8000/mcp/streamable_http"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List MCP tools via LangChain")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"MCP streamable HTTP endpoint (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--call",
        metavar="TOOL_NAME",
        help="Call a tool by name after loading tools",
    )
    parser.add_argument(
        "--args",
        default="{}",
        help="JSON string of tool arguments when using --call",
    )
    return parser.parse_args()


async def _call_tool(tools, tool_name: str, args_json: str) -> None:
    tool = next((t for t in tools if t.name == tool_name), None)
    if tool is None:
        available = ", ".join(sorted(t.name for t in tools))
        raise ValueError(f"Tool '{tool_name}' not found. Available: {available}")
    try:
        tool_args = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"--args must be valid JSON: {exc}") from exc
    result = await tool.ainvoke(tool_args)
    print("Tool result:")
    print(result)


async def _main(url: str, tool_name: str | None, args_json: str) -> None:
    client = MultiServerMCPClient(
        {
            "mcp_server": {
                "transport": "http",
                "url": url,
            }
        }
    )
    tools = await client.get_tools(server_name="mcp_server")
    print(f"Found {len(tools)} tools from {url}\n")
    for tool in tools:
        print(f"- {tool.name}")
        if tool.description:
            print(f"  {tool.description}")
        if getattr(tool, "args", None):
            print(f"  args: {tool.args}")
        print()
    if tool_name:
        await _call_tool(tools, tool_name, args_json)


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(_main(args.url, args.call, args.args))
