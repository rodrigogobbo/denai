"""Rotas de undo/redo."""

from __future__ import annotations

from fastapi import APIRouter

from ..undo import get_status, redo, undo

router = APIRouter()


@router.get("/api/undo/status")
async def undo_status():
    """Status do undo/redo."""
    return get_status()


@router.post("/api/undo")
async def do_undo():
    """Desfaz a última alteração."""
    return undo()


@router.post("/api/redo")
async def do_redo():
    """Refaz a última alteração desfeita."""
    return redo()
