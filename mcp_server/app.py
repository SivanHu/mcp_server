import json
import logging
from logging.handlers import RotatingFileHandler
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
from sse_starlette.sse import EventSourceResponse

from .db import get_tool, list_tools

app = FastAPI(title="mcp-server")

MCP_JSONRPC_VERSION = "2.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("mcp-server")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    file_handler = RotatingFileHandler(
        "mcp_server.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False


def _to_mcp_tool(tool: dict) -> dict:
    input_schema = tool.get("inputSchema") or {}
    if not isinstance(input_schema, dict):
        input_schema = {}
    schema_type = input_schema.get("type")
    if schema_type != "object":
        schema_type = "object"
    return {
        "name": tool["tool_name"],
        "description": tool.get("description") or "",
        "inputSchema": {
            "type": schema_type,
            "properties": input_schema.get("properties") or {},
            "required": input_schema.get("required") or [],
        },
    }


def _jsonrpc_result(req_id: str | int | None, result: dict) -> JSONResponse:
    return JSONResponse({"jsonrpc": MCP_JSONRPC_VERSION, "id": req_id, "result": result})


def _jsonrpc_error(req_id: str | int | None, code: int, message: str) -> JSONResponse:
    return JSONResponse({"jsonrpc": MCP_JSONRPC_VERSION, "id": req_id, "error": {"code": code, "message": message}})


async def _call_tool_http(tool: dict, arguments: dict | None) -> dict:
    url = tool.get("req_url")
    if not url:
        return {
            "content": [{"type": "text", "text": "Tool is missing req_url"}],
            "isError": True,
        }

    method = (tool.get("req_method") or "POST").upper()
    headers = tool.get("req_header") or {}
    if not isinstance(headers, dict):
        headers = {}

    params = None
    json_body = None
    if method in {"GET", "DELETE"}:
        params = arguments or {}
    else:
        json_body = arguments or {}

    logger.info(
        "tool_request tool=%s method=%s url=%s headers=%s params=%s json=%s",
        tool.get("tool_name"),
        method,
        url,
        json.dumps(headers, ensure_ascii=False),
        json.dumps(params, ensure_ascii=False) if params is not None else None,
        json.dumps(json_body, ensure_ascii=False) if json_body is not None else None,
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
            )
        structured: dict[str, Any] | None = None
        text = resp.text
        try:
            data = resp.json()
            structured = data if isinstance(data, dict) else {"data": data}
            text = json.dumps(data, ensure_ascii=False)
        except Exception:
            pass

        if resp.is_error:
            logger.info(
                "tool_response tool=%s status=%s error=true body=%s",
                tool.get("tool_name"),
                resp.status_code,
                text,
            )
            return {
                "content": [{"type": "text", "text": f"HTTP {resp.status_code}: {text}"}],
                "structuredContent": structured,
                "isError": True,
            }

        logger.info(
            "tool_response tool=%s status=%s error=false body=%s",
            tool.get("tool_name"),
            resp.status_code,
            text,
        )
        return {
            "content": [{"type": "text", "text": text}],
            "structuredContent": structured,
            "isError": False,
        }
    except Exception as exc:
        logger.exception("tool_response tool=%s error=true exception=%s", tool.get("tool_name"), exc)
        return {
            "content": [{"type": "text", "text": f"Request failed: {exc}"}],
            "isError": True,
        }


@app.get("/mcp/tools")
def mcp_tools():
    # Dynamic read from DB on each request
    return {"tools": list_tools()}


@app.get("/mcp/tools/{name}")
def mcp_tool(name: str):
    tool = get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail="tool not found")
    return tool


@app.get("/mcp/sse")
async def mcp_sse(tool_name: str | None = Query(None, description="Tool name")):
    async def event_gen() -> AsyncGenerator[dict, None]:
        if tool_name:
            tool = get_tool(tool_name)
            if not tool:
                yield {"event": "error", "data": json.dumps({"error": "tool not found"})}
                return
            yield {"event": "tool", "data": json.dumps(tool)}
            return
        yield {"event": "tools", "data": json.dumps(list_tools())}

    return EventSourceResponse(event_gen())


@app.post("/mcp/streamable_http")
async def mcp_streamable_http(
    request: Request, tool_name: str | None = Query(None, description="Tool name")
):
    # If Cherry Studio posts JSON-RPC, respond with a single JSON object (not a stream).
    try:
        body = await request.json()
    except Exception:
        body = None

    if isinstance(body, dict) and "method" in body:
        req_id = body.get("id")
        method = body.get("method")
        if method in ("initialize", "mcp:initialize"):
            # Minimal MCP initialize response
            return _jsonrpc_result(
                req_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": {"name": "mcp-server", "version": "0.1.0"},
                },
            )
        if method in ("notifications/initialized", "mcp:initialized"):
            return _jsonrpc_result(req_id, {})
        if method in ("mcp:list-tools", "tools/list"):
            tools = [_to_mcp_tool(t) for t in list_tools()]
            return _jsonrpc_result(req_id, {"tools": tools})
        if method in ("tools/call",):
            params = body.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not name:
                return _jsonrpc_error(req_id, -32602, "Missing tool name")
            tool = get_tool(name)
            if not tool:
                return _jsonrpc_error(req_id, -32602, f"Tool not found: {name}")
            logger.info(
                "tool_call name=%s args=%s",
                name,
                json.dumps(arguments, ensure_ascii=False),
            )
            result = await _call_tool_http(tool, arguments)
            logger.info(
                "tool_result name=%s result=%s",
                name,
                json.dumps(result, ensure_ascii=False),
            )
            return _jsonrpc_result(req_id, result)
        return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")

    if tool_name:
        tool = get_tool(tool_name)
        if not tool:
            return JSONResponse(status_code=404, content={"error": "tool not found"})
        payload = {"type": "tool", "data": tool}
    else:
        payload = {"type": "tools", "data": list_tools()}

    async def body() -> AsyncGenerator[bytes, None]:
        # Stream in chunks to simulate streamable HTTP
        yield json.dumps({"type": "start"}).encode("utf-8") + b"\n"
        yield json.dumps(payload).encode("utf-8") + b"\n"
        yield json.dumps({"type": "end"}).encode("utf-8") + b"\n"

    return StreamingResponse(body(), media_type="application/json")
