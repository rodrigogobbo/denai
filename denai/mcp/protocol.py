"""MCP protocol types and message formatting (JSON-RPC 2.0)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpTool:
    """A tool exposed by an MCP server."""

    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)
    server_name: str = ""

    def to_ollama_spec(self) -> dict:
        """Convert to Ollama/OpenAI tool spec format."""
        return {
            "type": "function",
            "function": {
                "name": self.prefixed_name,
                "description": f"[MCP:{self.server_name}] {self.description}",
                "parameters": self.input_schema,
            },
        }

    @property
    def prefixed_name(self) -> str:
        """Tool name prefixed with server name to avoid collisions."""
        if self.server_name:
            return f"mcp_{self.server_name}_{self.name}"
        return f"mcp_{self.name}"


@dataclass
class McpServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True


def make_request(method: str, params: dict | None = None, req_id: int = 1) -> str:
    """Create a JSON-RPC 2.0 request."""
    msg: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
    }
    if params is not None:
        msg["params"] = params
    return json.dumps(msg)


def parse_response(data: str) -> dict:
    """Parse a JSON-RPC 2.0 response."""
    try:
        msg = json.loads(data)
    except json.JSONDecodeError as e:
        return {"error": {"code": -32700, "message": f"Parse error: {e}"}}

    if "error" in msg:
        return {"error": msg["error"]}
    return {"result": msg.get("result", {}), "id": msg.get("id")}


def make_initialize(client_name: str = "denai", client_version: str = "0.11.0") -> str:
    """Create MCP initialize request."""
    return make_request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": client_name,
                "version": client_version,
            },
        },
        req_id=1,
    )


def make_initialized_notification() -> str:
    """Create MCP initialized notification (no id = notification)."""
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
    )


def make_tools_list() -> str:
    """Create tools/list request."""
    return make_request("tools/list", req_id=2)


def make_tools_call(tool_name: str, arguments: dict, req_id: int = 3) -> str:
    """Create tools/call request."""
    return make_request(
        "tools/call",
        {
            "name": tool_name,
            "arguments": arguments,
        },
        req_id=req_id,
    )
