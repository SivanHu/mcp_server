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

## Agent routing (choose tool automatically)

```bash
export OPENAI_API_KEY=YOUR_KEY
python agent.py --url http://127.0.0.1:8000/mcp/streamable_http \
  --input "根据今天的销售数据生成报表"
```

Optional:
- `--model` to choose an LLM model (default: gpt-4o-mini)
- `--base-url` to use an OpenAI-compatible endpoint (or set `OPENAI_BASE_URL`)
- `--max-steps` to control tool-calling rounds

## Fixed pipeline (no ReAct, tool order is preset)

Configure pipelines in `pipelines.json`, then run:

```bash
export OPENAI_API_KEY=YOUR_KEY
python pipeline_agent.py --url http://127.0.0.1:8000/mcp/streamable_http \
  --input "请把1和2相加"
```

Optional:
- `--pipeline` to force a specific pipeline by name
- `--pipelines` to use a different config file
