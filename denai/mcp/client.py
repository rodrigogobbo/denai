"""MCP client — connects to MCP servers via stdio subprocess."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from ..logging_config import get_logger
from .protocol import (
    McpServerConfig,
    McpTool,
    make_initialize,
    make_initialized_notification,
    make_tools_call,
    make_tools_list,
    parse_response,
)

log = get_logger("mcp")

# Global registry of connected MCP servers
_servers: dict[str, McpConnection] = {}


class McpConnection:
    """Connection to a single MCP server via stdio."""

    def __init__(self, config: McpServerConfig):
        self.config = config
        self.process: asyncio.subprocess.Process | None = None
        self.tools: list[McpTool] = []
        self._req_counter = 10
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected and self.process is not None and self.process.returncode is None

    async def connect(self) -> bool:
        """Start the MCP server process and perform handshake."""
        try:
            env = {**os.environ, **self.config.env}
            self.process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Initialize handshake
            resp = await self._send(make_initialize())
            if "error" in resp:
                log.error("MCP init failed for %s: %s", self.config.name, resp["error"])
                await self.disconnect()
                return False

            # Send initialized notification
            await self._write(make_initialized_notification())

            # Discover tools
            resp = await self._send(make_tools_list())
            if "error" in resp:
                log.error("MCP tools/list failed for %s: %s", self.config.name, resp["error"])
                await self.disconnect()
                return False

            result = resp.get("result", {})
            raw_tools = result.get("tools", [])
            self.tools = [
                McpTool(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                    server_name=self.config.name,
                )
                for t in raw_tools
                if t.get("name")
            ]

            self._connected = True
            log.info(
                "MCP server '%s' connected — %d tools discovered",
                self.config.name,
                len(self.tools),
            )
            return True

        except FileNotFoundError:
            log.error("MCP server command not found: %s", self.config.command)
            return False
        except Exception as e:
            log.error("MCP connect error for %s: %s", self.config.name, e)
            await self.disconnect()
            return False

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool on this MCP server."""
        if not self.connected:
            return f"❌ MCP server '{self.config.name}' not connected"

        self._req_counter += 1
        resp = await self._send(make_tools_call(tool_name, arguments, req_id=self._req_counter))

        if "error" in resp:
            return f"❌ MCP error: {resp['error']}"

        result = resp.get("result", {})
        # MCP tools/call returns content array
        content = result.get("content", [])
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(item.get("text", ""))
                    else:
                        parts.append(json.dumps(item))
                else:
                    parts.append(str(item))
            return "\n".join(parts) if parts else json.dumps(result)
        return json.dumps(result)

    async def disconnect(self):
        """Stop the MCP server process."""
        self._connected = False
        if self.process:
            try:
                self.process.stdin.close()  # type: ignore[union-attr]
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.process.kill()
            except Exception:
                pass
            self.process = None
        self.tools = []
        log.info("MCP server '%s' disconnected", self.config.name)

    async def _send(self, message: str) -> dict:
        """Send a JSON-RPC message and wait for response."""
        await self._write(message)
        return await self._read()

    async def _write(self, message: str) -> None:
        """Write a message to the process stdin."""
        if not self.process or not self.process.stdin:
            raise ConnectionError("Process not running")
        data = message.encode("utf-8")
        self.process.stdin.write(data + b"\n")
        await self.process.stdin.drain()

    async def _read(self, timeout: float = 30.0) -> dict:
        """Read a JSON-RPC response from stdout."""
        if not self.process or not self.process.stdout:
            return {"error": {"code": -1, "message": "Process not running"}}
        try:
            line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=timeout,
            )
            if not line:
                return {"error": {"code": -1, "message": "EOF from MCP server"}}

            text = line.decode("utf-8").strip()
            if not text:
                return {"error": {"code": -1, "message": "Empty response"}}

            return parse_response(text)
        except asyncio.TimeoutError:
            return {"error": {"code": -1, "message": "Timeout waiting for MCP response"}}
        except Exception as e:
            return {"error": {"code": -1, "message": str(e)}}


# ─── Global MCP management ───


def load_mcp_configs() -> list[McpServerConfig]:
    """Load MCP server configs from ~/.denai/config.yaml."""
    from ..config import _yaml_cfg

    servers_cfg = _yaml_cfg.get("mcp_servers", {})
    if not isinstance(servers_cfg, dict):
        return []

    configs: list[McpServerConfig] = []
    for name, cfg in servers_cfg.items():
        if not isinstance(cfg, dict):
            continue
        configs.append(
            McpServerConfig(
                name=str(name),
                command=cfg.get("command", ""),
                args=cfg.get("args", []),
                env=cfg.get("env", {}),
                enabled=cfg.get("enabled", True),
            )
        )

    return configs


async def connect_server(config: McpServerConfig) -> bool:
    """Connect to an MCP server."""
    if config.name in _servers:
        await disconnect_server(config.name)

    conn = McpConnection(config)
    success = await conn.connect()
    if success:
        _servers[config.name] = conn
    return success


async def disconnect_server(name: str) -> bool:
    """Disconnect an MCP server."""
    conn = _servers.pop(name, None)
    if conn:
        await conn.disconnect()
        return True
    return False


async def disconnect_all():
    """Disconnect all MCP servers."""
    names = list(_servers.keys())
    for name in names:
        await disconnect_server(name)


def get_connected_servers() -> dict[str, McpConnection]:
    """Get all connected MCP servers."""
    return dict(_servers)


def get_all_mcp_tools() -> tuple[list[dict], dict[str, Any]]:
    """Get tool specs and executors from all connected MCP servers.

    Returns (specs, executors) in the same format as the tool registry.
    """
    specs: list[dict] = []
    executors: dict[str, Any] = {}

    for conn in _servers.values():
        if not conn.connected:
            continue
        for tool in conn.tools:
            specs.append(tool.to_ollama_spec())
            # Create a closure for this specific tool
            _conn = conn
            _tool_name = tool.name

            async def _executor(args: dict, c=_conn, t=_tool_name) -> str:
                return await c.call_tool(t, args)

            executors[tool.prefixed_name] = _executor

    return specs, executors
