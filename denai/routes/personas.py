"""Rotas de personas — listar personas disponíveis."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..personas import discover_personas

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("")
async def list_personas() -> dict[str, Any]:
    """Lista todas as personas disponíveis (bundled + custom)."""
    personas = discover_personas()
    return {
        "personas": [
            {
                "name": p.name,
                "description": p.description,
                "source": p.source,
            }
            for p in personas
        ]
    }
