"""Tests for MCP (Model Context Protocol) support."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from denai.mcp.client import (
    McpConnection,
    _servers,
    disconnect_all,
    disconnect_server,
    get_all_mcp_tools,
    get_connected_servers,
    load_mcp_configs,
)
from denai.mcp.protocol import (
    McpServerConfig,
    McpTool,
    make_initialize,
    make_initialized_notification,
    make_tools_call,
    make_tools_list,
    parse_response,
)
from denai.security.auth import API_KEY

# ─── Protocol tests ───


class TestMcpTool:
    """Test MCP tool representation."""

    def test_basic(self):
        tool = McpTool(name="read_file", description="Read a file", server_name="fs")
        assert tool.name == "read_file"
        assert tool.prefixed_name == "mcp_fs_read_file"

    def test_to_ollama_spec(self):
        tool = McpTool(
            name="search",
            description="Search the web",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            server_name="web",
        )
        spec = tool.to_ollama_spec()
        assert spec["type"] == "function"
        assert spec["function"]["name"] == "mcp_web_search"
        assert "[MCP:web]" in spec["function"]["description"]
        assert "query" in spec["function"]["parameters"]["properties"]

    def test_no_server_name(self):
        tool = McpTool(name="test")
        assert tool.prefixed_name == "mcp_test"

    def test_empty_schema(self):
        tool = McpTool(name="ping", server_name="s")
        spec = tool.to_ollama_spec()
        assert spec["function"]["parameters"] == {}


class TestMcpServerConfig:
    """Test server config."""

    def test_basic(self):
        cfg = McpServerConfig(name="test", command="node", args=["server.js"])
        assert cfg.name == "test"
        assert cfg.enabled is True

    def test_with_env(self):
        cfg = McpServerConfig(name="db", command="python", env={"DB_URL": "sqlite:///test"})
        assert cfg.env["DB_URL"] == "sqlite:///test"


class TestProtocolMessages:
    """Test JSON-RPC message creation."""

    def test_make_initialize(self):
        msg = json.loads(make_initialize())
        assert msg["jsonrpc"] == "2.0"
        assert msg["method"] == "initialize"
        assert msg["id"] == 1
        assert "clientInfo" in msg["params"]
        assert msg["params"]["clientInfo"]["name"] == "denai"

    def test_make_initialized(self):
        msg = json.loads(make_initialized_notification())
        assert "id" not in msg  # notifications have no id
        assert msg["method"] == "notifications/initialized"

    def test_make_tools_list(self):
        msg = json.loads(make_tools_list())
        assert msg["method"] == "tools/list"
        assert msg["id"] == 2

    def test_make_tools_call(self):
        msg = json.loads(make_tools_call("read_file", {"path": "/tmp/test"}, req_id=5))
        assert msg["method"] == "tools/call"
        assert msg["params"]["name"] == "read_file"
        assert msg["params"]["arguments"]["path"] == "/tmp/test"
        assert msg["id"] == 5


class TestParseResponse:
    """Test response parsing."""

    def test_success(self):
        resp = parse_response('{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}')
        assert "result" in resp
        assert resp["result"]["tools"] == []

    def test_error(self):
        resp = parse_response('{"jsonrpc":"2.0","id":1,"error":{"code":-1,"message":"fail"}}')
        assert "error" in resp
        assert resp["error"]["code"] == -1

    def test_invalid_json(self):
        resp = parse_response("not json")
        assert "error" in resp
        assert "Parse error" in resp["error"]["message"]

    def test_empty_result(self):
        resp = parse_response('{"jsonrpc":"2.0","id":1}')
        assert resp["result"] == {}


# ─── Client tests ───


class TestMcpConnection:
    """Test MCP connection management."""

    def test_initial_state(self):
        cfg = McpServerConfig(name="test", command="echo")
        conn = McpConnection(cfg)
        assert conn.connected is False
        assert conn.tools == []

    @pytest.mark.asyncio
    async def test_connect_command_not_found(self):
        cfg = McpServerConfig(name="test", command="/nonexistent/binary")
        conn = McpConnection(cfg)
        result = await conn.connect()
        assert result is False
        assert conn.connected is False

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        cfg = McpServerConfig(name="test", command="echo")
        conn = McpConnection(cfg)
        result = await conn.call_tool("test", {})
        assert "not connected" in result

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self):
        cfg = McpServerConfig(name="test", command="echo")
        conn = McpConnection(cfg)
        await conn.disconnect()  # Should not raise
        assert conn.connected is False


class TestMcpGlobalManagement:
    """Test global server management."""

    def setup_method(self):
        _servers.clear()

    @pytest.mark.asyncio
    async def test_get_connected_empty(self):
        assert get_connected_servers() == {}

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self):
        assert await disconnect_server("nope") is False

    @pytest.mark.asyncio
    async def test_disconnect_all_empty(self):
        await disconnect_all()  # Should not raise

    def test_get_all_mcp_tools_empty(self):
        specs, executors = get_all_mcp_tools()
        assert specs == []
        assert executors == {}

    def test_load_configs_empty(self):
        with patch("denai.mcp.client._yaml_cfg", {}, create=True), patch("denai.config._yaml_cfg", {}, create=True):
            configs = load_mcp_configs()
            assert configs == []

    def test_load_configs(self):
        fake_cfg = {
            "mcp_servers": {
                "filesystem": {
                    "command": "node",
                    "args": ["fs-server.js"],
                    "env": {"HOME": "/tmp"},
                },
                "web": {
                    "command": "python",
                    "args": ["-m", "web_mcp"],
                    "enabled": False,
                },
            }
        }
        with patch("denai.config._yaml_cfg", fake_cfg):
            configs = load_mcp_configs()
            assert len(configs) == 2
            fs_cfg = next(c for c in configs if c.name == "filesystem")
            web_cfg = next(c for c in configs if c.name == "web")
            assert fs_cfg.command == "node"
            assert fs_cfg.args == ["fs-server.js"]
            assert fs_cfg.enabled is True
            assert web_cfg.name == "web"
            assert web_cfg.enabled is False

    def test_load_configs_invalid(self):
        with patch("denai.config._yaml_cfg", {"mcp_servers": "not a dict"}):
            configs = load_mcp_configs()
            assert configs == []


class TestMcpToolIntegration:
    """Test MCP tool registration in registry."""

    def setup_method(self):
        _servers.clear()

    def test_mcp_tools_with_mock_server(self):
        """Test that MCP tools get proper specs and executors."""
        cfg = McpServerConfig(name="test", command="echo")
        conn = McpConnection(cfg)
        conn._connected = True
        conn.process = MagicMock()
        conn.process.returncode = None
        conn.tools = [
            McpTool(name="hello", description="Say hello", server_name="test"),
            McpTool(
                name="add",
                description="Add numbers",
                input_schema={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
                server_name="test",
            ),
        ]
        _servers["test"] = conn

        specs, executors = get_all_mcp_tools()
        assert len(specs) == 2
        assert len(executors) == 2
        assert "mcp_test_hello" in executors
        assert "mcp_test_add" in executors
        assert specs[0]["function"]["name"] == "mcp_test_hello"
        assert "[MCP:test]" in specs[0]["function"]["description"]


# ─── API tests ───


def _setup_mcp_router():
    """Register MCP router on the app if not already registered."""
    from denai.app import app
    from denai.routes.mcp import router as mcp_router

    # Check if routes already exist
    existing_paths = {r.path for r in app.routes if hasattr(r, "path")}
    if "/api/mcp/servers" not in existing_paths:
        app.include_router(mcp_router)
    return app


@pytest.mark.asyncio
class TestMcpAPI:
    """Test MCP API endpoints."""

    def setup_method(self):
        _servers.clear()

    async def _get(self, client: AsyncClient, path: str):
        return await client.get(path, headers={"X-API-Key": API_KEY})

    async def _post(self, client: AsyncClient, path: str, body: dict = None):
        return await client.post(path, json=body or {}, headers={"X-API-Key": API_KEY})

    async def test_list_servers_empty(self):
        app = _setup_mcp_router()
        with patch("denai.routes.mcp.load_mcp_configs", return_value=[]):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await self._get(client, "/api/mcp/servers")
                assert resp.status_code == 200
                assert resp.json()["servers"] == []

    async def test_connect_missing_name(self):
        app = _setup_mcp_router()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await self._post(client, "/api/mcp/connect", {})
            data = resp.json()
            assert "error" in data

    async def test_disconnect_missing(self):
        app = _setup_mcp_router()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await self._post(client, "/api/mcp/disconnect", {"name": "nonexistent"})
            data = resp.json()
            assert data.get("ok") is False

    async def test_disconnect_all(self):
        app = _setup_mcp_router()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await self._post(client, "/api/mcp/disconnect-all")
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

    async def test_connect_not_found_in_config(self):
        app = _setup_mcp_router()
        with patch("denai.routes.mcp.load_mcp_configs", return_value=[]):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await self._post(client, "/api/mcp/connect", {"name": "nope"})
                data = resp.json()
                assert "error" in data
