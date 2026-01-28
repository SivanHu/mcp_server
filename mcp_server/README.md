# MCP Server (Cherry Studio Compatible)

A minimal MCP-compatible server for Cherry Studio using **Streamable HTTP** or **SSE**. Tool metadata is loaded dynamically from a **MySQL** database and exposed as MCP tools.

This README is designed for quick deployment on any Linux/WSL machine.

---

## 1) Features

- MCP JSON-RPC (initialize + tools/list) compatibility for Cherry Studio
- Streamable HTTP endpoint
- Optional SSE endpoint
- MySQL-backed tool registry
- Tool schema normalization (ensures `inputSchema.type` is `object`)

---

## 2) Requirements

- Python 3.10+
- MySQL 8.x

---

## 3) Folder Structure

```
mcp_server/
  app.py
  db.py
  init_db.py
  requirements.txt
  README.md
```

---

## 4) Install

### 4.1 Create venv

```
python -m venv .venv
source .venv/bin/activate
```

### 4.2 Install dependencies

```
pip install -r requirements.txt
```

---

## 5) MySQL Setup

### 5.1 Create database and user (example)

```sql
CREATE DATABASE IF NOT EXISTS mcp;
CREATE USER IF NOT EXISTS 'mcp_user'@'%' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON mcp.* TO 'mcp_user'@'%';
FLUSH PRIVILEGES;
```

### 5.2 Environment variables

```bash
export MCP_DB_HOST=127.0.0.1
export MCP_DB_PORT=3306
export MCP_DB_USER=mcp_user
export MCP_DB_PASSWORD=strong_password
export MCP_DB_NAME=mcp
```

---

## 6) Initialize Table + Example Tool

```bash
python -m mcp_server.init_db
```

This will create a `tools` table and insert a sample tool.

---

## 7) Run Server

```bash
uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000
```

### Run in background

```bash
nohup uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000 > uvicorn.out 2>&1 &
```

---

## 8) MCP Endpoints

### Streamable HTTP (Cherry Studio)

```
POST http://<server_ip>:8000/mcp/streamable_http
```

### SSE (optional)

```
GET http://<server_ip>:8000/mcp/sse
```

### Tool list (debug)

```
GET http://<server_ip>:8000/mcp/tools
```

---

## 9) Cherry Studio Configuration

In Cherry Studio MCP settings:

- **Type**: Streamable HTTP
- **URL**: `http://<server_ip>:8000/mcp/streamable_http`

If you are running on WSL and Cherry Studio is on Windows, use the WSL IP as `<server_ip>`:

```bash
ip addr show eth0 | grep inet
```

---

## 10) Database Schema

The server expects the following columns in `tools`:

- `tool_name` (PK)
- `description`
- `inputSchema_type`
- `inputSchema_properties` (JSON)
- `inputSchema_required` (JSON)
- `req_url`
- `req_header` (JSON)
- `req_method`
- `outputSchema_description`

Extra columns are allowed and will be ignored.

---

## 11) Common Issues

### 11.1 Cherry Studio error: Method not found initialize
- Make sure you are running the updated `app.py` that supports JSON-RPC `initialize`.

### 11.2 JSON parse error from Cherry Studio
- Use the **Streamable HTTP URL** (not the SSE URL) in Cherry Studio.

### 11.3 Port already in use
- Stop old processes:
```
pkill -f "uvicorn mcp_server.app:app"
```

---

## 12) Security Notes

- Do not use weak passwords in production.
- Restrict MySQL user host from `%` to your trusted subnet if possible.

---

## 13) Next Steps (optional)

- Add `tools/call` method to actually execute tools
- Add auth middleware
- Add caching for large tool lists
