# mcp-client

Use LangChain MCP adapters to list and call tools exposed by the MCP server.

## Setup

```bash
source /home/sivan/venv/langchain/bin/activate
```

## List tools

```bash
python list_tools.py --url http://127.0.0.1:8000/mcp/streamable_http
```

## Call a tool

```bash
python list_tools.py --url http://127.0.0.1:8000/mcp/streamable_http \
  --call TOOL_NAME \
  --args '{"param1":"value"}'
```

Notes:
- `--args` must be valid JSON.
- If your server URL changes, pass it with `--url`.
