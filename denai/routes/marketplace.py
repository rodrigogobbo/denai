"""Rotas do marketplace de plugins."""

from __future__ import annotations

from fastapi import APIRouter

from ..marketplace import get_registry, install_plugin, uninstall_plugin

router = APIRouter()


@router.get("/api/marketplace")
async def list_marketplace():
    """Lista plugins disponíveis no marketplace."""
    return {"plugins": get_registry()}


@router.post("/api/marketplace/install")
async def install(body: dict):
    """Instala um plugin do marketplace."""
    plugin_id = body.get("plugin_id", "")
    if not plugin_id:
        return {"error": "plugin_id é obrigatório"}
    return install_plugin(plugin_id)


@router.post("/api/marketplace/uninstall")
async def uninstall(body: dict):
    """Remove um plugin instalado."""
    plugin_id = body.get("plugin_id", "")
    if not plugin_id:
        return {"error": "plugin_id é obrigatório"}
    return uninstall_plugin(plugin_id)
