"""Registry de tools — autodiscovery + plugins + dispatcher."""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from pathlib import Path

from ..logging_config import get_logger
from ..plugins import discover_plugins, get_plugin_tools

log = get_logger("tools")

# Registros globais
TOOLS_SPEC: list[dict] = []
_EXECUTORS: dict[str, Callable] = {}


def _discover_tools():
    """Descobre e registra todas as tools do pacote denai.tools.*"""
    package_dir = Path(__file__).parent

    for _importer, module_name, _ispkg in pkgutil.iter_modules([str(package_dir)]):
        if module_name == "registry":
            continue  # Pula a si mesmo

        module = importlib.import_module(f".{module_name}", package="denai.tools")

        # Cada módulo deve ter TOOLS = [(spec_dict, "function_name"), ...]
        tools_list = getattr(module, "TOOLS", [])
        for spec, func_name in tools_list:
            TOOLS_SPEC.append(spec)
            executor = getattr(module, func_name, None)
            if executor:
                _EXECUTORS[func_name] = executor


def _discover_plugin_tools():
    """Descobre e registra tools de plugins em ~/.denai/plugins/."""
    try:
        discover_plugins()
        specs, executors = get_plugin_tools()
        TOOLS_SPEC.extend(specs)
        _EXECUTORS.update(executors)
    except Exception:
        pass  # Plugins são opcionais — erros não devem quebrar o boot


def refresh_mcp_tools():
    """Refresh MCP tools in the registry from connected MCP servers.

    Call after connecting/disconnecting MCP servers to sync the
    TOOLS_SPEC and _EXECUTORS with currently available MCP tools.
    """
    # Remove existing MCP tools
    mcp_specs = [s for s in TOOLS_SPEC if s.get("function", {}).get("name", "").startswith("mcp_")]
    for spec in mcp_specs:
        TOOLS_SPEC.remove(spec)

    mcp_keys = [k for k in _EXECUTORS if k.startswith("mcp_")]
    for key in mcp_keys:
        del _EXECUTORS[key]

    # Re-inject from connected servers
    try:
        from ..mcp.client import get_all_mcp_tools

        specs, executors = get_all_mcp_tools()
        TOOLS_SPEC.extend(specs)
        _EXECUTORS.update(executors)
        log.info("MCP tools refreshed — %d tools from MCP servers", len(specs))
    except ImportError:
        pass  # MCP module not available
    except Exception as e:
        log.error("Error refreshing MCP tools: %s", e)


async def execute_tool(name: str, args: dict) -> str:
    """Dispatcher — executa uma tool pelo nome, respeitando permissões."""
    executor = _EXECUTORS.get(name)
    if not executor:
        log.warning("Tool desconhecida chamada: %s", name)
        return f"❌ Tool desconhecida: {name}"

    # Checar permissão
    try:
        from ..permissions import check_permission

        perm = check_permission(name)
        if not perm.allowed and perm.level == "deny":
            log.warning("Tool %s bloqueada por permissão (deny)", name)
            return f"🚫 Tool '{name}' está bloqueada. Altere em /api/permissions."
    except ImportError:
        pass  # Permissions module não disponível — permite tudo

    try:
        result = await executor(args)
        log.debug("Tool %s executada — args=%s", name, list(args.keys()))
        return result
    except PermissionError:
        target = args.get("path", args.get("command", "?"))
        log.warning("PermissionError na tool %s: %s", name, target)
        return f"🔒 Sem permissão: {target}"
    except Exception as e:
        log.error("Erro na tool %s: %s: %s", name, type(e).__name__, e, exc_info=True)
        return f"❌ Erro: {type(e).__name__}: {str(e)}"


# Auto-discover no import
_discover_tools()
_discover_plugin_tools()
