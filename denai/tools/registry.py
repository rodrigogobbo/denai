"""Registry de tools — autodiscovery + dispatcher."""

import importlib
import pkgutil
from pathlib import Path
from typing import Callable

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


async def execute_tool(name: str, args: dict) -> str:
    """Dispatcher — executa uma tool pelo nome."""
    executor = _EXECUTORS.get(name)
    if not executor:
        return f"❌ Tool desconhecida: {name}"

    try:
        return await executor(args)
    except PermissionError:
        return f"🔒 Sem permissão: {args.get('path', args.get('command', '?'))}"
    except Exception as e:
        return f"❌ Erro: {type(e).__name__}: {str(e)}"


# Auto-discover no import
_discover_tools()
