import json
import os

import pymysql

DB_HOST = os.environ.get("MCP_DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("MCP_DB_PORT", "3306"))
DB_USER = os.environ.get("MCP_DB_USER", "admin")
DB_PASSWORD = os.environ.get("MCP_DB_PASSWORD", "123")
DB_NAME = os.environ.get("MCP_DB_NAME", "tool")


def main() -> None:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
    )
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_list (
            tool_name VARCHAR(255) PRIMARY KEY,
            description TEXT NOT NULL,
            inputSchema_type VARCHAR(64) NOT NULL,
            inputSchema_properties JSON NOT NULL,
            inputSchema_required JSON NOT NULL,
            req_url TEXT NOT NULL,
            req_header JSON NOT NULL,
            req_method VARCHAR(16) NOT NULL,
            outputSchema_description TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        INSERT INTO tool_list (
            tool_name, description, inputSchema_type, inputSchema_properties,
            inputSchema_required, req_url, req_header, req_method, outputSchema_description
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            description=VALUES(description),
            inputSchema_type=VALUES(inputSchema_type),
            inputSchema_properties=VALUES(inputSchema_properties),
            inputSchema_required=VALUES(inputSchema_required),
            req_url=VALUES(req_url),
            req_header=VALUES(req_header),
            req_method=VALUES(req_method),
            outputSchema_description=VALUES(outputSchema_description)
        """,
        (
            "example_tool",
            "Echo input for testing",
            "object",
            json.dumps(
                {
                    "text": {"type": "string", "description": "Input text"},
                    "count": {"type": "integer", "description": "Repeat count"},
                }
            ),
            json.dumps(["text"]),
            "https://api.example.com/v1/echo",
            json.dumps({"Authorization": "Bearer <token>"}),
            "POST",
            "Returns the echoed input",
        ),
    )
    conn.close()
    print(f"DB initialized on {DB_HOST}:{DB_PORT}, database={DB_NAME}")


if __name__ == "__main__":
    main()
