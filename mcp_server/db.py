import json
import os
from typing import Any, Dict, List, Optional

import pymysql

DB_HOST = os.environ.get("MCP_DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("MCP_DB_PORT", "3306"))
DB_USER = os.environ.get("MCP_DB_USER", "admin")
DB_PASSWORD = os.environ.get("MCP_DB_PASSWORD", "123")
DB_NAME = os.environ.get("MCP_DB_NAME", "tool")


def _connect() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def list_tools() -> List[Dict[str, Any]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tool_name, description, inputSchema_type, inputSchema_properties, "
                "inputSchema_required, req_url, req_header, req_method, outputSchema_description "
                "FROM tool_list ORDER BY tool_name"
            )
            rows = cur.fetchall()
    return [_row_to_tool(row) for row in rows]


def get_tool(name: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tool_name, description, inputSchema_type, inputSchema_properties, "
                "inputSchema_required, req_url, req_header, req_method, outputSchema_description "
                "FROM tool_list WHERE tool_name = %s",
                (name,),
            )
            row = cur.fetchone()
    return _row_to_tool(row) if row else None


def _row_to_tool(row: Dict[str, Any]) -> Dict[str, Any]:
    properties = row["inputSchema_properties"]
    required = row["inputSchema_required"]
    headers = row["req_header"]
    if isinstance(properties, str):
        properties = json.loads(properties or "{}")
    if isinstance(required, str):
        required = json.loads(required or "[]")
    if isinstance(headers, str):
        headers = json.loads(headers or "{}")
    return {
        "tool_name": row["tool_name"],
        "description": row["description"],
        "inputSchema": {
            "type": row["inputSchema_type"],
            "properties": properties,
            "required": required,
        },
        "req_url": row["req_url"],
        "req_header": headers,
        "req_method": row["req_method"],
        "outputSchema": {
            "description": row["outputSchema_description"],
        },
    }
