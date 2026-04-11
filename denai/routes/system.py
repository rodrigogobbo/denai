"""Rota de perfil do sistema — hardware + recomendação de modelo."""

from __future__ import annotations

from fastapi import APIRouter

from ..system_profile import get_system_profile

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/profile")
async def system_profile():
    """Retorna perfil de hardware e recomendação de modelo LLM."""
    return await get_system_profile()
