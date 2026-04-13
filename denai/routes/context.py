"""Rotas de contexto de repositório — /api/context/*."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..context_store import (
    activate_context,
    deactivate_context,
    get_context,
    list_active_contexts,
)

router = APIRouter(prefix="/api/context", tags=["context"])


class ActivateBody(BaseModel):
    path: str
    conversation_id: str


@router.post("/activate")
async def activate(body: ActivateBody):
    """Ativa contexto de repositório para uma conversa."""
    result = activate_context(body.conversation_id, body.path)
    if not result["ok"]:
        return JSONResponse({"error": result["error"]}, status_code=400)
    return result


@router.delete("/{conv_id}")
async def deactivate(conv_id: str):
    """Desativa contexto de uma conversa."""
    removed = deactivate_context(conv_id)
    return {"ok": removed}


@router.get("/{conv_id}")
async def get_active_context(conv_id: str):
    """Retorna o contexto ativo de uma conversa."""
    ctx = get_context(conv_id)
    if not ctx:
        return {"active": False}
    return {
        "active": True,
        "project_name": ctx["project_name"],
        "path": ctx["path"],
        "file_count": ctx["file_count"],
    }


@router.get("")
async def list_contexts():
    """Lista todos os contextos ativos (admin)."""
    return {"contexts": list_active_contexts()}
