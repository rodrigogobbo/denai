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
    except ValueError:
        return JSONResponse({"error": "Operação inválida. Verifique o nome do perfil."}, status_code=400)


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
    except ValueError:
        return JSONResponse({"error": "Operação inválida. Verifique o nome do perfil."}, status_code=400)


@router.delete("/{name}")
async def remove_profile(name: str):
    """Remove um perfil e seus dados."""
    try:
        removed = delete_profile(name)
        if not removed:
            return JSONResponse({"error": f"Perfil '{name}' não encontrado."}, status_code=404)
        return {"ok": True}
    except ValueError:
        return JSONResponse({"error": "Operação inválida. Verifique o nome do perfil."}, status_code=400)


# ── Modelo por perfil ─────────────────────────────────────────────────────


class ModelBody(BaseModel):
    model: str


@router.get("/active/model")
async def get_active_model():
    """Retorna o último modelo usado no perfil ativo."""
    from ..profile_manager import get_active_profile, get_profile_dir

    profile_dir = get_profile_dir(get_active_profile())
    last_model_file = profile_dir / "last_model"
    if last_model_file.exists():
        model = last_model_file.read_text(encoding="utf-8").strip()
        if model:
            return {"model": model}
    return {"model": None}


@router.post("/active/model")
async def save_active_model(body: ModelBody):
    """Persiste o modelo selecionado no perfil ativo."""
    model = body.model.strip()
    if not model:
        return JSONResponse({"error": "model é obrigatório."}, status_code=400)
    from ..profile_manager import get_active_profile, get_profile_dir

    profile_dir = get_profile_dir(get_active_profile())
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "last_model").write_text(model, encoding="utf-8")
    return {"ok": True, "model": model}
