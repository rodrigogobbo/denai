"""Rotas de gerenciamento de perfis."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..profile_manager import (
    create_profile,
    delete_profile,
    get_active_profile,
    list_profiles,
    set_active_profile,
)

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("")
async def get_profiles():
    """Lista todos os perfis disponíveis."""
    return {"profiles": list_profiles(), "active": get_active_profile()}


@router.get("/active")
async def active_profile():
    """Retorna o perfil atualmente ativo."""
    return {"active": get_active_profile()}


class ProfileBody(BaseModel):
    name: str


@router.post("", status_code=201)
async def create_new_profile(body: ProfileBody):
    """Cria um novo perfil."""
    try:
        profile_dir = create_profile(body.name)
        return {"ok": True, "name": body.name, "dir": str(profile_dir)}
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/{name}/activate")
async def activate_profile(name: str):
    """Ativa um perfil. O cliente deve recarregar a página."""
    try:
        set_active_profile(name)
        return {
            "ok": True,
            "active": name,
            "message": "Perfil ativado. Recarregue a página para aplicar.",
            "reload": True,
        }
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.delete("/{name}")
async def remove_profile(name: str):
    """Remove um perfil e seus dados."""
    try:
        removed = delete_profile(name)
        if not removed:
            return JSONResponse({"error": f"Perfil '{name}' não encontrado."}, status_code=404)
        return {"ok": True}
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
