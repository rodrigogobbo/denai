"""Rotas de plugins — listar, recarregar."""

from fastapi import APIRouter

from ..plugins import discover_plugins, list_plugins

router = APIRouter()


@router.get("/api/plugins")
async def get_plugins():
    """Lista plugins instalados em ~/.denai/plugins/."""
    return {"plugins": list_plugins()}


@router.post("/api/plugins/reload")
async def reload_plugins():
    """Recarrega plugins (redescobre ~/.denai/plugins/)."""

    # Limpar tools de plugins anteriores e redescobrir
    # (mantém tools built-in, recarrega apenas plugins)
    # Nota: como não temos tracking de quais são de plugins,
    # por simplicidade redescobre tudo
    discover_plugins()

    return {"plugins": list_plugins(), "message": "Plugins recarregados"}
