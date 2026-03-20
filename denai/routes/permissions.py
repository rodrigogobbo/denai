"""Rotas de permissões granulares."""

from __future__ import annotations

from fastapi import APIRouter

from ..permissions import (
    check_permission,
    get_all_permissions,
    reset_permissions,
    set_permission,
)

router = APIRouter()


@router.get("/api/permissions")
async def list_permissions():
    """Lista todas as permissões atuais."""
    perms = get_all_permissions()
    return {
        "permissions": {
            tool: {"level": level, "description": _describe(level)} for tool, level in sorted(perms.items())
        }
    }


@router.put("/api/permissions")
async def update_permission(body: dict):
    """Atualiza a permissão de uma tool."""
    tool = body.get("tool", "")
    level = body.get("level", "")

    if not tool:
        return {"error": "Campo 'tool' é obrigatório"}
    if level not in ("allow", "ask", "deny"):
        return {"error": "Campo 'level' deve ser allow, ask ou deny"}

    set_permission(tool, level)
    return {"ok": True, "tool": tool, "level": level}


@router.post("/api/permissions/reset")
async def reset_all_permissions():
    """Reset all permissions to defaults."""
    reset_permissions()
    return {"ok": True, "message": "Permissões resetadas para defaults"}


@router.post("/api/permissions/check")
async def check_tool_permission(body: dict):
    """Check if a tool is allowed."""
    tool = body.get("tool", "")
    if not tool:
        return {"error": "Campo 'tool' é obrigatório"}
    result = check_permission(tool)
    return {
        "tool": result.tool,
        "allowed": result.allowed,
        "level": result.level,
        "reason": result.reason,
    }


def _describe(level: str) -> str:
    return {
        "allow": "Executa sem pedir confirmação",
        "ask": "Pede confirmação antes de executar",
        "deny": "Bloqueada — não executa",
    }.get(level, "Desconhecido")
