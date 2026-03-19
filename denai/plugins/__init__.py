"""Sistema de plugins do DenAI.

Plugins são módulos Python em ~/.denai/plugins/ que estendem as
capacidades do DenAI. Cada plugin é um diretório com:

    ~/.denai/plugins/
    └── meu_plugin/
        ├── plugin.json      ← metadata (nome, versão, tools)
        └── main.py          ← código do plugin (TOOLS + funções)

Ou um arquivo .py simples:
    ~/.denai/plugins/
    └── meu_plugin.py        ← TOOLS + funções (metadata via docstring)
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from ..config import DATA_DIR

PLUGINS_DIR = DATA_DIR / "plugins"
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

# Registros
_loaded_plugins: list[dict] = []


def _load_module_from_path(name: str, path: Path):
    """Carrega um módulo Python a partir de um caminho absoluto."""
    spec = importlib.util.spec_from_file_location(f"denai_plugin_{name}", str(path))
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"denai_plugin_{name}"] = module
    spec.loader.exec_module(module)
    return module


def discover_plugins() -> list[dict]:
    """Descobre e carrega plugins de ~/.denai/plugins/.

    Returns:
        Lista de metadados dos plugins carregados.
    """
    global _loaded_plugins
    _loaded_plugins = []

    if not PLUGINS_DIR.exists():
        return _loaded_plugins

    for item in sorted(PLUGINS_DIR.iterdir()):
        try:
            if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
                # Single-file plugin
                plugin_info = _load_single_file_plugin(item)
                if plugin_info:
                    _loaded_plugins.append(plugin_info)

            elif item.is_dir() and not item.name.startswith("_"):
                # Directory plugin
                plugin_info = _load_directory_plugin(item)
                if plugin_info:
                    _loaded_plugins.append(plugin_info)
        except Exception as e:
            _loaded_plugins.append(
                {
                    "name": item.name,
                    "status": "error",
                    "error": f"{type(e).__name__}: {e}",
                    "tools": [],
                }
            )

    return _loaded_plugins


def _load_single_file_plugin(path: Path) -> dict | None:
    """Carrega plugin de arquivo único (.py)."""
    name = path.stem
    module = _load_module_from_path(name, path)
    if module is None:
        return None

    tools_list = getattr(module, "TOOLS", [])
    tools_specs = []
    executors = {}

    for spec, func_name in tools_list:
        tools_specs.append(spec)
        executor = getattr(module, func_name, None)
        if executor:
            executors[func_name] = executor

    return {
        "name": name,
        "version": getattr(module, "__version__", "0.1.0"),
        "description": (module.__doc__ or "").strip().split("\n")[0] if module.__doc__ else "",
        "status": "loaded",
        "tools": tools_specs,
        "executors": executors,
        "type": "single_file",
        "path": str(path),
    }


def _load_directory_plugin(directory: Path) -> dict | None:
    """Carrega plugin de diretório (com plugin.json + main.py)."""
    main_file = directory / "main.py"
    if not main_file.exists():
        return None

    name = directory.name

    # Load metadata from plugin.json if exists
    metadata = {"name": name, "version": "0.1.0", "description": ""}
    json_file = directory / "plugin.json"
    if json_file.exists():
        try:
            metadata.update(json.loads(json_file.read_text(encoding="utf-8")))
        except Exception:
            pass

    # Load the module
    module = _load_module_from_path(name, main_file)
    if module is None:
        return None

    tools_list = getattr(module, "TOOLS", [])
    tools_specs = []
    executors = {}

    for spec, func_name in tools_list:
        tools_specs.append(spec)
        executor = getattr(module, func_name, None)
        if executor:
            executors[func_name] = executor

    return {
        "name": metadata.get("name", name),
        "version": metadata.get("version", "0.1.0"),
        "description": metadata.get("description", ""),
        "status": "loaded",
        "tools": tools_specs,
        "executors": executors,
        "type": "directory",
        "path": str(directory),
    }


def get_plugin_tools() -> tuple[list[dict], dict]:
    """Retorna specs e executors de todos os plugins carregados.

    Returns:
        (specs_list, executors_dict)
    """
    all_specs = []
    all_executors = {}

    for plugin in _loaded_plugins:
        if plugin.get("status") == "loaded":
            all_specs.extend(plugin.get("tools", []))
            all_executors.update(plugin.get("executors", {}))

    return all_specs, all_executors


def list_plugins() -> list[dict]:
    """Retorna metadados dos plugins (sem executors)."""
    return [
        {
            "name": p["name"],
            "version": p.get("version", "0.1.0"),
            "description": p.get("description", ""),
            "status": p.get("status", "unknown"),
            "tools_count": len(p.get("tools", [])),
            "type": p.get("type", "unknown"),
            "path": p.get("path", ""),
            "error": p.get("error"),
        }
        for p in _loaded_plugins
    ]
