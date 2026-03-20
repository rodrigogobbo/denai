"""Granular permissions — allow/ask/deny per tool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import yaml

from .config import DATA_DIR
from .logging_config import get_logger

log = get_logger("permissions")

PermLevel = Literal["allow", "ask", "deny"]

# Default permission levels per tool
_DEFAULTS: dict[str, PermLevel] = {
    # Read-only tools — always allowed
    "file_read": "allow",
    "list_files": "allow",
    "grep": "allow",
    "think": "allow",
    "memory_search": "allow",
    "web_search": "allow",
    "web_fetch": "allow",
    "rag_search": "allow",
    "rag_stats": "allow",
    # Write tools — ask by default
    "file_write": "ask",
    "file_edit": "ask",
    "command_exec": "ask",
    "memory_save": "allow",
    "plan_create": "allow",
    "plan_update": "allow",
    "create_document": "ask",
    "create_spreadsheet": "ask",
    "rag_index": "ask",
    "git": "ask",
    # Interactive — always allowed
    "question": "allow",
}

PERMISSIONS_FILE = DATA_DIR / "permissions.yaml"


@dataclass
class PermissionResult:
    """Result of a permission check."""

    allowed: bool
    level: PermLevel
    tool: str
    reason: str = ""


def _load_overrides() -> dict[str, PermLevel]:
    """Load permission overrides from ~/.denai/permissions.yaml."""
    if not PERMISSIONS_FILE.is_file():
        return {}
    try:
        with open(PERMISSIONS_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        # Also check config.yaml for permissions section
        result: dict[str, PermLevel] = {}
        perms = data.get("permissions", data)  # support both root-level and nested
        for tool, level in perms.items():
            if level in ("allow", "ask", "deny"):
                result[str(tool)] = level
        return result
    except Exception as e:
        log.warning("Erro ao carregar permissions.yaml: %s", e)
        return {}


def _load_from_config_yaml() -> dict[str, PermLevel]:
    """Load permission overrides from ~/.denai/config.yaml permissions section."""
    config_path = DATA_DIR / "config.yaml"
    if not config_path.is_file():
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        perms = data.get("permissions", {})
        if not isinstance(perms, dict):
            return {}
        result: dict[str, PermLevel] = {}
        for tool, level in perms.items():
            if level in ("allow", "ask", "deny"):
                result[str(tool)] = level
        return result
    except Exception:
        return {}


def get_all_permissions() -> dict[str, PermLevel]:
    """Get merged permissions (defaults + config.yaml + permissions.yaml)."""
    merged = dict(_DEFAULTS)
    # config.yaml overrides defaults
    merged.update(_load_from_config_yaml())
    # permissions.yaml overrides everything
    merged.update(_load_overrides())
    return merged


def check_permission(tool_name: str) -> PermissionResult:
    """Check if a tool is allowed to execute."""
    perms = get_all_permissions()
    level = perms.get(tool_name, "ask")  # Unknown tools default to "ask"

    if level == "deny":
        return PermissionResult(
            allowed=False,
            level=level,
            tool=tool_name,
            reason=f"Tool '{tool_name}' está bloqueada (deny).",
        )

    if level == "allow":
        return PermissionResult(allowed=True, level=level, tool=tool_name)

    # "ask" — needs confirmation
    return PermissionResult(
        allowed=False,
        level="ask",
        tool=tool_name,
        reason=f"Tool '{tool_name}' requer confirmação.",
    )


def set_permission(tool_name: str, level: PermLevel) -> None:
    """Set a tool's permission level (persists to permissions.yaml)."""
    if level not in ("allow", "ask", "deny"):
        raise ValueError(f"Nível inválido: {level}. Use allow, ask ou deny.")

    overrides = _load_overrides()
    overrides[tool_name] = level

    PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PERMISSIONS_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump({"permissions": overrides}, f, default_flow_style=False)

    log.info("Permissão de '%s' alterada para '%s'", tool_name, level)


def reset_permissions() -> None:
    """Reset all permissions to defaults (removes permissions.yaml)."""
    if PERMISSIONS_FILE.is_file():
        PERMISSIONS_FILE.unlink()
    log.info("Permissões resetadas para defaults")
