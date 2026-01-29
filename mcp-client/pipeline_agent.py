import argparse
import asyncio
import json
import os
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

DEFAULT_URL = "http://127.0.0.1:8000/mcp/streamable_http"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_PIPELINES = os.path.join(os.path.dirname(__file__), "pipelines.json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a fixed tool pipeline with LLM-only parameter extraction"
    )
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
        "--pipelines",
        default=DEFAULT_PIPELINES,
        help=f"Pipeline config JSON (default: {DEFAULT_PIPELINES})",
    )
    parser.add_argument(
        "--pipeline",
        default="",
        help="Force a specific pipeline by name",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="User input",
    )
    return parser.parse_args()


def _ensure_openai_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")


def _load_pipelines(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _select_pipeline(pipelines: list[dict], user_input: str, forced: str) -> dict:
    if forced:
        for pipe in pipelines:
            if pipe.get("name") == forced:
                return pipe
        raise ValueError(f"Pipeline not found: {forced}")

    lowered = user_input.lower()
    for pipe in pipelines:
        keywords = pipe.get("keywords") or []
        if any(k.lower() in lowered for k in keywords):
            return pipe
    if not pipelines:
        raise ValueError("No pipelines defined")
    return pipelines[0]


def _extract_json(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model did not return JSON")
        data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("Extracted JSON must be an object")
    return data


async def _extract_args(llm: ChatOpenAI, prompt: str, context: dict) -> dict:
    system = (
        "You only extract arguments for a fixed tool. "
        "Return ONLY a JSON object. No extra text."
    )
    user = f"PROMPT:\n{prompt}\n\nCONTEXT JSON:\n{json.dumps(context, ensure_ascii=False)}"
    msg = await llm.ainvoke([HumanMessage(content=system), HumanMessage(content=user)])
    return _extract_json(msg.content)


async def _run(url: str, model: str, base_url: str, pipelines_path: str, forced: str, user_input: str) -> None:
    _ensure_openai_key()

    config = _load_pipelines(pipelines_path)
    pipeline = _select_pipeline(config.get("pipelines", []), user_input, forced)

    client = MultiServerMCPClient(
        {
            "mcp_server": {
                "transport": "http",
                "url": url,
            }
        }
    )
    tools = await client.get_tools(server_name="mcp_server")
    tool_map = {t.name: t for t in tools}

    llm = ChatOpenAI(model=model, temperature=0, base_url=base_url or None)

    print(f"Pipeline: {pipeline.get('name')}")
    context: dict[str, Any] = {"input": user_input, "steps": {}}

    for step in pipeline.get("steps", []):
        step_name = step.get("name") or "step"
        tool_name = step.get("tool")
        prompt = step.get("extract_prompt") or "Return {}"

        tool = tool_map.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")

        args = await _extract_args(llm, prompt, context)
        result = await tool.ainvoke(args)

        context["steps"][step_name] = {
            "tool": tool_name,
            "args": args,
            "result": result,
        }

        print(f"Step {step_name} -> {tool_name}")
        print(f"  args: {args}")
        print(f"  result: {result}")

    print("Done")


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        _run(
            args.url,
            args.model,
            args.base_url,
            args.pipelines,
            args.pipeline,
            args.input,
        )
    )
