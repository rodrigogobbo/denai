"""Rotas de skills."""

from __future__ import annotations

from fastapi import APIRouter

from ..skills import (
    activate_skill,
    clear_active_skills,
    deactivate_skill,
    discover_skills,
    get_active_skills,
    match_skills,
)

router = APIRouter()


@router.get("/api/skills")
async def list_skills():
    """Lista todas as skills disponíveis."""
    skills = discover_skills()
    active = {s.name for s in get_active_skills()}
    return {
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "triggers": s.triggers,
                "active": s.name in active,
                "auto_activate": s.auto_activate,
            }
            for s in skills
        ]
    }


@router.post("/api/skills/activate")
async def activate(body: dict):
    """Ativa uma skill pelo nome."""
    name = body.get("name", "")
    if not name:
        return {"error": "Campo 'name' é obrigatório"}
    ok = activate_skill(name)
    if not ok:
        return {"error": f"Skill '{name}' não encontrada"}
    return {"ok": True, "name": name, "active": True}


@router.post("/api/skills/deactivate")
async def deactivate(body: dict):
    """Desativa uma skill."""
    name = body.get("name", "")
    if not name:
        return {"error": "Campo 'name' é obrigatório"}
    deactivate_skill(name)
    return {"ok": True, "name": name, "active": False}


@router.post("/api/skills/match")
async def match(body: dict):
    """Encontra skills que seriam ativadas pelo texto dado."""
    text = body.get("text", "")
    matched = match_skills(text)
    return {"matched": [{"name": s.name, "description": s.description} for s in matched]}


@router.post("/api/skills/clear")
async def clear():
    """Limpa todas as skills ativas manualmente."""
    clear_active_skills()
    return {"ok": True, "message": "Skills desativadas"}
