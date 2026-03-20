"""Rotas de custom commands."""

from __future__ import annotations

from fastapi import APIRouter

from ..commands import discover_commands, get_command, render_command

router = APIRouter()


@router.get("/api/commands")
async def list_commands():
    """Lista todos os comandos disponíveis."""
    commands = discover_commands()
    return {
        "commands": [
            {
                "name": cmd.name,
                "description": cmd.description,
                "has_model": bool(cmd.model),
            }
            for cmd in commands
        ]
    }


@router.post("/api/commands/run")
async def run_command(body: dict):
    """Renderiza um comando com argumentos."""
    name = body.get("name", "")
    arguments = body.get("arguments", "")

    if not name:
        return {"error": "name é obrigatório"}

    cmd = get_command(name)
    if not cmd:
        return {"error": f"Comando '/{name}' não encontrado"}

    rendered = render_command(cmd, arguments)
    return {
        "ok": True,
        "prompt": rendered,
        "model": cmd.model,
        "name": cmd.name,
    }
