"""Rotas de MCP (Model Context Protocol)."""

from __future__ import annotations

from fastapi import APIRouter

from ..mcp.client import (
    McpServerConfig,
    connect_server,
    disconnect_all,
    disconnect_server,
    get_connected_servers,
    load_mcp_configs,
)
from ..tools.registry import refresh_mcp_tools

router = APIRouter()


@router.get("/api/mcp/servers")
async def list_servers():
    """Lista MCP servers configurados e status de conexão."""
    configs = load_mcp_configs()
    connected = get_connected_servers()

    servers = []
    for cfg in configs:
        conn = connected.get(cfg.name)
        servers.append(
            {
                "name": cfg.name,
                "command": cfg.command,
                "args": cfg.args,
                "enabled": cfg.enabled,
                "connected": conn.connected if conn else False,
                "tools_count": len(conn.tools) if conn else 0,
                "tools": [{"name": t.name, "description": t.description} for t in (conn.tools if conn else [])],
            }
        )

    return {"servers": servers}


@router.post("/api/mcp/connect")
async def connect(body: dict):
    """Conecta a um MCP server pelo nome (da config) ou por config inline."""
    name = body.get("name", "")

    if name:
        # Connect by name from config
        configs = load_mcp_configs()
        cfg = next((c for c in configs if c.name == name), None)
        if not cfg:
            return {"error": f"MCP server '{name}' não encontrado na config"}
    else:
        # Inline config
        command = body.get("command", "")
        if not command:
            return {"error": "Campo 'name' ou 'command' é obrigatório"}
        cfg = McpServerConfig(
            name=body.get("server_name", "custom"),
            command=command,
            args=body.get("args", []),
            env=body.get("env", {}),
        )

    success = await connect_server(cfg)
    if not success:
        return {"error": f"Falha ao conectar ao MCP server '{cfg.name}'"}

    refresh_mcp_tools()

    connected = get_connected_servers()
    conn = connected.get(cfg.name)
    return {
        "ok": True,
        "name": cfg.name,
        "tools_count": len(conn.tools) if conn else 0,
        "tools": [{"name": t.name, "description": t.description} for t in (conn.tools if conn else [])],
    }


@router.post("/api/mcp/disconnect")
async def disconnect(body: dict):
    """Desconecta um MCP server."""
    name = body.get("name", "")
    if not name:
        return {"error": "Campo 'name' é obrigatório"}
    ok = await disconnect_server(name)
    refresh_mcp_tools()
    return {"ok": ok, "name": name}


@router.post("/api/mcp/disconnect-all")
async def disconnect_all_servers():
    """Desconecta todos os MCP servers."""
    await disconnect_all()
    refresh_mcp_tools()
    return {"ok": True}


@router.post("/api/mcp/connect-all")
async def connect_all():
    """Conecta a todos os MCP servers habilitados na config."""
    configs = load_mcp_configs()
    results = []

    for cfg in configs:
        if not cfg.enabled:
            results.append({"name": cfg.name, "connected": False, "reason": "disabled"})
            continue
        success = await connect_server(cfg)
        connected = get_connected_servers()
        conn = connected.get(cfg.name)
        results.append(
            {
                "name": cfg.name,
                "connected": success,
                "tools_count": len(conn.tools) if conn else 0,
            }
        )

    refresh_mcp_tools()
    return {"results": results}
