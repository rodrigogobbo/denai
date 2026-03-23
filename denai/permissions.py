"""Granular permissions — allow/ask/deny per tool."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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

_VALID_LEVELS = frozenset({"allow", "ask", "deny"})


@dataclass
class PermissionResult:
    """Result of a permission check."""

    allowed: bool
    level: PermLevel
    tool: str
    reason: str = ""


def _load_yaml_perms(filepath: Path, section_key: str | None = None) -> dict[str, PermLevel]:
    """Load permission overrides from a YAML file.

    If *section_key* is given, look for a nested dict under that key first,
    falling back to the root dict.  Returns an empty dict on any error.
    """
    if not filepath.is_file():
        return {}
    try:
        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        perms = data.get(section_key, data) if section_key else data
        if not isinstance(perms, dict):
            return {}
        return {str(tool): level for tool, level in perms.items() if level in _VALID_LEVELS}
    except Exception as e:
        log.warning("Erro ao carregar %s: %s", filepath, e)
        return {}


def _load_overrides() -> dict[str, PermLevel]:
    """Load permission overrides from ~/.denai/permissions.yaml."""
    return _load_yaml_perms(PERMISSIONS_FILE, section_key="permissions")


def _load_from_config_yaml() -> dict[str, PermLevel]:
    """Load permission overrides from ~/.denai/config.yaml permissions section."""
    return _load_yaml_perms(DATA_DIR / "config.yaml", section_key="permissions")


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
    if level not in _VALID_LEVELS:
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
